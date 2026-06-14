from __future__ import annotations

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class GdeltConnector(HttpDiscoveryConnector):
    source_name = "gdelt"
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"

    def discover(
        self,
        query: str,
        timespan: str = "1week",
        max_results: int | None = None,
        language: str = "",
    ):
        result = self.new_result(query=query, timespan=timespan)
        limit = max_results or self.max_results
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": limit,
            "timespan": timespan,
        }
        if language:
            params["sourcelang"] = language

        data = self.request_json(result, self.endpoint, params=params)
        if not data:
            return result

        candidates = []
        for item in data.get("articles", []):
            url = item.get("url", "")
            if not url:
                continue

            candidates.append(
                UrlCandidate(
                    url=url,
                    discovered_from="gdelt",
                    query=query,
                    source_type="news",
                    priority=65,
                    metadata={
                        "provider": "gdelt",
                        "title": item.get("title", ""),
                        "domain": item.get("domain", ""),
                        "published_at": item.get("seendate", "") or item.get("socialimage", ""),
                        "language": item.get("language", ""),
                        "source_country": item.get("sourcecountry", ""),
                    },
                )
            )

        result.candidates = self.limit_candidates(candidates, limit)
        result.metadata["candidate_count"] = len(result.candidates)
        return result
