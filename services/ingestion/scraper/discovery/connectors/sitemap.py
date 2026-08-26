from __future__ import annotations

from lxml import etree
from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class SitemapConnector(HttpDiscoveryConnector):
    source_name = "sitemap"

    def discover(
        self,
        sitemap_url: str,
        source_type: str = "unknown",
        priority: int = 50,
        country_tags: list[str] | None = None,
        topic_tags: list[str] | None = None,
        query: str = "",
        max_results: int | None = None,
        max_child_sitemaps: int = 10,
    ):
        result = self.new_result(sitemap_url=sitemap_url)
        candidates = self.parse_sitemap(
            result=result,
            sitemap_url=sitemap_url,
            source_type=source_type,
            priority=priority,
            country_tags=country_tags or [],
            topic_tags=topic_tags or [],
            query=query or sitemap_url,
            max_results=max_results or self.max_results,
            max_child_sitemaps=max_child_sitemaps,
            depth=0,
        )
        result.candidates = candidates[: max_results or self.max_results]
        result.metadata["candidate_count"] = len(result.candidates)
        return result

    def parse_sitemap(
        self,
        result,
        sitemap_url: str,
        source_type: str,
        priority: int,
        country_tags: list[str],
        topic_tags: list[str],
        query: str,
        max_results: int,
        max_child_sitemaps: int,
        depth: int,
    ) -> list[UrlCandidate]:
        content = self.request_bytes(result, sitemap_url)
        if not content:
            return []

        try:
            root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
        except Exception as error:
            result.add_error(str(error), code="invalid_xml", metadata={"sitemap_url": sitemap_url})
            return []

        root_name = self.local_name(root)

        if root_name == "sitemapindex" and depth == 0:
            candidates = []
            child_urls = [
                self.child_text(child, "loc")
                for child in self.iter_by_local(root, "sitemap")
                if self.child_text(child, "loc")
            ][:max_child_sitemaps]

            for child_url in child_urls:
                if len(candidates) >= max_results:
                    break

                candidates.extend(
                    self.parse_sitemap(
                        result=result,
                        sitemap_url=child_url,
                        source_type=source_type,
                        priority=priority,
                        country_tags=country_tags,
                        topic_tags=topic_tags,
                        query=query,
                        max_results=max_results - len(candidates),
                        max_child_sitemaps=max_child_sitemaps,
                        depth=depth + 1,
                    )
                )

            return candidates

        candidates = []
        for url_element in self.iter_by_local(root, "url"):
            loc = self.child_text(url_element, "loc")
            if not loc:
                continue

            candidates.append(
                UrlCandidate(
                    url=loc,
                    discovered_from="sitemap",
                    query=query,
                    source_type=source_type,
                    priority=priority,
                    country_tags=country_tags,
                    topic_tags=topic_tags,
                    metadata={
                        "provider": "sitemap",
                        "sitemap_url": sitemap_url,
                        "lastmod": self.child_text(url_element, "lastmod"),
                    },
                )
            )

            if len(candidates) >= max_results:
                break

        return candidates

    def child_text(self, element, name: str) -> str:
        for child in element:
            if self.local_name(child) == name:
                return (child.text or "").strip()

        return ""

    def iter_by_local(self, root, name: str):
        for element in root.iter():
            if self.local_name(element) == name:
                yield element

    def local_name(self, element) -> str:
        return etree.QName(element).localname
