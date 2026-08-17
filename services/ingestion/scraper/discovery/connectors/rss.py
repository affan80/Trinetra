from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any

from lxml import etree

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class RssConnector(HttpDiscoveryConnector):
    source_name = "rss"

    def discover(
        self,
        feed_url: str,
        source_type: str = "news",
        priority: int = 50,
        country_tags: list[str] | None = None,
        topic_tags: list[str] | None = None,
        query: str = "",
        max_results: int | None = None,
    ):
        result = self.new_result(feed_url=feed_url)
        content = self.request_bytes(result, feed_url)
        if not content:
            return result

        try:
            root = etree.fromstring(content, parser=etree.XMLParser(recover=True))
        except Exception as error:
            result.add_error(str(error), code="invalid_xml", metadata={"feed_url": feed_url})
            return result

        candidates = []
        for entry in self.extract_entries(root):
            url = entry.get("url", "")
            if not url:
                continue

            candidates.append(
                UrlCandidate(
                    url=url,
                    discovered_from="rss",
                    query=query or feed_url,
                    source_type=source_type,
                    priority=priority,
                    country_tags=country_tags or [],
                    topic_tags=topic_tags or [],
                    metadata={
                        "provider": "rss",
                        "feed_url": feed_url,
                        "title": entry.get("title", ""),
                        "published_at": entry.get("published_at", ""),
                    },
                )
            )

        result.candidates = self.limit_candidates(candidates, max_results)
        result.metadata["candidate_count"] = len(result.candidates)
        return result

    def extract_entries(self, root) -> list[dict[str, Any]]:
        root_name = self.local_name(root)

        if root_name == "feed":
            return [self.parse_atom_entry(entry) for entry in self.iter_by_local(root, "entry")]

        return [self.parse_rss_item(item) for item in self.iter_by_local(root, "item")]

    def parse_rss_item(self, item) -> dict[str, str]:
        return {
            "url": self.child_text(item, "link"),
            "title": self.child_text(item, "title"),
            "published_at": self.normalize_date(
                self.child_text(item, "pubDate") or self.child_text(item, "published")
            ),
        }

    def parse_atom_entry(self, entry) -> dict[str, str]:
        link = ""
        for child in entry:
            if self.local_name(child) == "link":
                link = child.attrib.get("href", "") or child.text or ""
                if link:
                    break

        return {
            "url": link,
            "title": self.child_text(entry, "title"),
            "published_at": self.child_text(entry, "updated") or self.child_text(entry, "published"),
        }

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

    def normalize_date(self, value: str) -> str:
        if not value:
            return ""

        try:
            return parsedate_to_datetime(value).isoformat()
        except Exception:
            return value
