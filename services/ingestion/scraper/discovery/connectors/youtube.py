from __future__ import annotations

import os

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class YouTubeConnector(HttpDiscoveryConnector):
    source_name = "youtube"
    endpoint = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")

    def discover(
        self,
        query: str,
        max_results: int | None = None,
        published_after: str = "",
        region_code: str = "IN",
    ):
        result = self.new_result(query=query)
        if not self.api_key:
            result.add_error("Missing YOUTUBE_API_KEY", code="missing_credentials", recoverable=False)
            return result

        limit = min(max_results or self.max_results, 50)
        params = {
            "key": self.api_key,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": limit,
            "regionCode": region_code,
        }
        if published_after:
            params["publishedAfter"] = published_after

        data = self.request_json(result, self.endpoint, params=params)
        if not data:
            return result

        candidates = []
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            if not video_id:
                continue

            candidates.append(
                UrlCandidate(
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    discovered_from="platform",
                    query=query,
                    source_type="video",
                    priority=55,
                    country_tags=[region_code] if region_code else [],
                    metadata={
                        "provider": "youtube",
                        "video_id": video_id,
                        "channel_id": snippet.get("channelId", ""),
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt", ""),
                    },
                )
            )

        result.candidates = candidates
        result.metadata["candidate_count"] = len(result.candidates)
        return result
