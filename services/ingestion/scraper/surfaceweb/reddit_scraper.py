from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

DEFAULT_KEYWORDS = [
    "hack",
    "cyber",
    "attack",
    "breach",
    "war",
    "military",
    "exploit",
    "leak",
]


@dataclass
class RedditCollectorResult:
    items: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


class RedditScraper:
    def __init__(
        self,
        session: requests.Session | None = None,
        user_agent: str | None = None,
        timeout_seconds: int = 15,
        retries: int = 2,
        rate_limit_seconds: float = 1.0,
    ):
        self.session = session or requests.Session()
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT", "TrinetraOSINT/1.0")
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.rate_limit_seconds = rate_limit_seconds
        self.seen = set()

    def collect(
        self,
        subreddits: list[str] | None = None,
        query: str = "",
        keywords: list[str] | None = None,
        limit: int = 25,
        pages: int = 1,
        sort: str = "new",
    ) -> RedditCollectorResult:
        result = RedditCollectorResult()
        keywords = keywords if keywords is not None else DEFAULT_KEYWORDS

        for subreddit in subreddits or []:
            self.fetch_subreddit(result, subreddit, keywords, limit, pages, sort)

        if query:
            self.fetch_search(result, query, keywords, limit, pages, sort)

        return result

    def fetch_subreddit(self, result, subreddit: str, keywords: list[str], limit: int, pages: int, sort: str) -> None:
        after = ""

        for _ in range(max(1, pages)):
            params = {"limit": min(limit, 100)}
            if after:
                params["after"] = after

            data = self.safe_request(f"https://www.reddit.com/r/{subreddit}/{sort}.json", params, result)
            if not data:
                return

            after = data.get("data", {}).get("after") or ""
            self.add_posts(result, data, keywords, subreddit=subreddit)

            if not after:
                return

    def fetch_search(self, result, query: str, keywords: list[str], limit: int, pages: int, sort: str) -> None:
        after = ""

        for _ in range(max(1, pages)):
            params = {
                "q": query,
                "sort": sort,
                "limit": min(limit, 100),
            }
            if after:
                params["after"] = after

            data = self.safe_request("https://www.reddit.com/search.json", params, result)
            if not data:
                return

            after = data.get("data", {}).get("after") or ""
            self.add_posts(result, data, keywords)

            if not after:
                return

    def safe_request(self, url: str, params: dict[str, Any], result: RedditCollectorResult) -> dict[str, Any] | None:
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                    timeout=self.timeout_seconds,
                )
                if response.status_code == 200:
                    if self.rate_limit_seconds:
                        time.sleep(self.rate_limit_seconds)
                    return response.json()

                recoverable = response.status_code in {408, 429, 500, 502, 503, 504}
                result.errors.append({
                    "code": f"http_{response.status_code}",
                    "message": f"Reddit returned HTTP {response.status_code}",
                    "recoverable": recoverable,
                    "url": url,
                })
                if not recoverable:
                    return None

            except Exception as error:
                result.errors.append({
                    "code": error.__class__.__name__,
                    "message": str(error),
                    "recoverable": True,
                    "url": url,
                })

            if attempt < self.retries:
                time.sleep(min(2 ** attempt, 8))

        return None

    def add_posts(self, result: RedditCollectorResult, data: dict[str, Any], keywords: list[str], subreddit: str = "") -> None:
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            post_id = post.get("id", "")
            title = post.get("title", "")

            if not post_id or post_id in self.seen:
                continue

            if keywords and not self.is_relevant(title, keywords):
                continue

            self.seen.add(post_id)
            result.items.append({
                "id": post_id,
                "text": title,
                "subreddit": post.get("subreddit", subreddit),
                "source": "reddit",
                "timestamp": post.get("created_utc", ""),
                "url": post.get("url", ""),
                "permalink": self.build_permalink(post.get("permalink", "")),
                "score": post.get("score", 0),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

    def is_relevant(self, text: str, keywords: list[str]) -> bool:
        text = (text or "").lower()
        return any(keyword.lower() in text for keyword in keywords)

    def build_permalink(self, permalink: str) -> str:
        if not permalink:
            return ""
        if permalink.startswith("http"):
            return permalink
        return f"https://www.reddit.com{permalink}"
