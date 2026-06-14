from __future__ import annotations

import os

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class BraveSearchConnector(HttpDiscoveryConnector):
    source_name = "brave_search"

    endpoints = {
        "web": "https://api.search.brave.com/res/v1/web/search",
        "news": "https://api.search.brave.com/res/v1/news/search",
        "image": "https://api.search.brave.com/res/v1/images/search",
        "video": "https://api.search.brave.com/res/v1/videos/search",
    }

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")

    def discover(
        self,
        query: str,
        search_type: str = "web",
        country: str = "IN",
        language: str = "en",
        freshness: str = "",
        max_results: int | None = None,
    ):
        result = self.new_result(query=query, search_type=search_type)
        if not self.api_key:
            result.add_error("Missing BRAVE_SEARCH_API_KEY", code="missing_credentials", recoverable=False)
            return result

        endpoint = self.endpoints.get(search_type, self.endpoints["web"])
        limit = max_results or self.max_results
        params = {
            "q": query,
            "country": country,
            "search_lang": language,
            "count": min(limit, 20),
        }
        if freshness:
            params["freshness"] = freshness

        data = self.request_json(
            result,
            endpoint,
            params=params,
            headers={"X-Subscription-Token": self.api_key},
        )
        if not data:
            return result

        candidates = []
        for item in self.extract_items(data, search_type):
            url = item.get("url") or item.get("properties", {}).get("url", "")
            if not url:
                continue

            candidates.append(
                UrlCandidate(
                    url=url,
                    discovered_from="brave_search",
                    query=query,
                    source_type=self.source_type_for_search(search_type),
                    priority=60,
                    country_tags=[country] if country else [],
                    metadata={
                        "provider": "brave_search",
                        "search_type": search_type,
                        "title": item.get("title", ""),
                        "snippet": item.get("description", ""),
                        "published_at": item.get("age", ""),
                    },
                )
            )

        result.candidates = self.limit_candidates(candidates, limit)
        result.metadata["candidate_count"] = len(result.candidates)
        return result

    def extract_items(self, data: dict, search_type: str) -> list[dict]:
        if search_type == "web":
            return data.get("web", {}).get("results", [])

        if search_type == "news":
            return data.get("news", {}).get("results", [])

        if search_type == "image":
            return data.get("results") or data.get("images", {}).get("results", [])

        if search_type == "video":
            return data.get("results") or data.get("videos", {}).get("results", [])

        return []

    def source_type_for_search(self, search_type: str) -> str:
        if search_type == "news":
            return "news"
        if search_type == "image":
            return "image"
        if search_type == "video":
            return "video"
        return "unknown"
