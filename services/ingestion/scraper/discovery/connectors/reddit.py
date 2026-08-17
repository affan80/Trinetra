from __future__ import annotations

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors.base import HttpDiscoveryConnector


class RedditConnector(HttpDiscoveryConnector):
    source_name = "reddit"

    def discover(
        self,
        subreddits: list[str] | None = None,
        query: str = "",
        sort: str = "new",
        limit: int = 25,
        pages: int = 1,
    ):
        result = self.new_result(query=query, subreddits=subreddits or [])
        candidates = []

        for subreddit in subreddits or []:
            candidates.extend(self.discover_subreddit(result, subreddit, sort, limit, pages))

        if query:
            candidates.extend(self.discover_search(result, query, sort, limit, pages))

        result.candidates = self.limit_candidates(candidates)
        result.metadata["candidate_count"] = len(result.candidates)
        return result

    def discover_subreddit(self, result, subreddit: str, sort: str, limit: int, pages: int) -> list[UrlCandidate]:
        candidates = []
        after = ""

        for _ in range(max(1, pages)):
            params = {"limit": min(limit, 100)}
            if after:
                params["after"] = after

            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
            data = self.request_json(result, url, params=params, headers=self.reddit_headers())
            if not data:
                break

            after = data.get("data", {}).get("after") or ""
            candidates.extend(self.items_to_candidates(data, query=f"r/{subreddit}", subreddit=subreddit))

            if not after:
                break

        return candidates

    def discover_search(self, result, query: str, sort: str, limit: int, pages: int) -> list[UrlCandidate]:
        candidates = []
        after = ""

        for _ in range(max(1, pages)):
            params = {
                "q": query,
                "sort": sort,
                "limit": min(limit, 100),
            }
            if after:
                params["after"] = after

            data = self.request_json(result, "https://www.reddit.com/search.json", params=params, headers=self.reddit_headers())
            if not data:
                break

            after = data.get("data", {}).get("after") or ""
            candidates.extend(self.items_to_candidates(data, query=query))

            if not after:
                break

        return candidates

    def items_to_candidates(self, data: dict, query: str, subreddit: str = "") -> list[UrlCandidate]:
        candidates = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            permalink = post.get("permalink", "")
            url = post.get("url") or ""
            if not url.startswith(("http://", "https://")) and permalink:
                url = f"https://www.reddit.com{permalink}"

            if not url:
                continue

            candidates.append(
                UrlCandidate(
                    url=url,
                    discovered_from="platform",
                    query=query,
                    source_type="social",
                    priority=45,
                    metadata={
                        "provider": "reddit",
                        "post_id": post.get("id", ""),
                        "subreddit": post.get("subreddit", subreddit),
                        "title": post.get("title", ""),
                        "author": post.get("author", ""),
                        "score": post.get("score", 0),
                        "created_utc": post.get("created_utc", ""),
                        "permalink": f"https://www.reddit.com{permalink}" if permalink else "",
                    },
                )
            )

        return candidates

    def reddit_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.default_headers.get("User-Agent", "TrinetraOSINT/1.0"),
            "Accept": "application/json",
        }
