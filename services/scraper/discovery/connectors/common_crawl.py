from __future__ import annotations

import json

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class CommonCrawlConnector(HttpDiscoveryConnector):
    source_name = "common_crawl"

    def discover(
        self,
        url_pattern: str,
        crawl: str = "",
        match_type: str = "prefix",
        filters: list[str] | None = None,
        max_results: int | None = None,
        source_type: str = "unknown",
    ):
        result = self.new_result(url_pattern=url_pattern, crawl=crawl)
        if not crawl:
            result.add_error("Common Crawl index name is required", code="missing_crawl_index", recoverable=False)
            return result

        endpoint = f"https://index.commoncrawl.org/{crawl}-index"
        params = {
            "url": url_pattern,
            "output": "json",
            "matchType": match_type,
        }

        for item_filter in filters or ["status:200"]:
            params.setdefault("filter", item_filter)

        text = self.request_text(result, endpoint, params=params)
        if not text:
            return result

        candidates = []
        for line in text.splitlines():
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                result.add_error("Invalid Common Crawl JSON line", code="invalid_json_line")
                continue

            url = item.get("url", "")
            if not url:
                continue

            candidates.append(
                UrlCandidate(
                    url=url,
                    discovered_from="common_crawl",
                    query=url_pattern,
                    source_type=source_type,
                    priority=30,
                    metadata={
                        "provider": "common_crawl",
                        "crawl": crawl,
                        "timestamp": item.get("timestamp", ""),
                        "status": item.get("status", ""),
                        "mime": item.get("mime", ""),
                        "digest": item.get("digest", ""),
                    },
                )
            )

            if len(candidates) >= (max_results or self.max_results):
                break

        result.candidates = candidates
        result.metadata["candidate_count"] = len(result.candidates)
        return result
