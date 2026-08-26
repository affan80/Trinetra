from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

DISCOVERY_SOURCES = {
    "brave_search",
    "rss",
    "sitemap",
    "gdelt",
    "common_crawl",
    "manual",
    "platform",
}

SOURCE_TYPES = {
    "news",
    "blog",
    "social",
    "video",
    "image",
    "gov",
    "think_tank",
    "unknown",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_priority(value: Any) -> int:
    try:
        priority = int(value)
    except (TypeError, ValueError):
        priority = 50

    return max(0, min(priority, 100))


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    else:
        values = list(value)

    normalized = []
    seen = set()

    for item in values:
        text = str(item).strip()
        key = text.lower()

        if text and key not in seen:
            seen.add(key)
            normalized.append(text)

    return normalized


def normalize_web_url(url: str) -> str:
    url = str(url or "").strip()

    if not url:
        return ""

    parsed = urlparse(url)

    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return url

    if not parsed.netloc:
        return url

    path = parsed.path or "/"

    return urlunparse((
        parsed.scheme.lower() or "https",
        parsed.netloc.lower(),
        path,
        "",
        parsed.query,
        "",
    ))


@dataclass
class UrlCandidate:
    url: str
    discovered_from: str
    query: str = ""
    source_type: str = "unknown"
    priority: int = 50
    country_tags: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.url = normalize_web_url(self.url)
        self.discovered_from = self.normalize_discovered_from(self.discovered_from)
        self.source_type = self.normalize_source_type(self.source_type)
        self.priority = clamp_priority(self.priority)
        self.country_tags = normalize_list(self.country_tags)
        self.topic_tags = normalize_list(self.topic_tags)
        self.metadata = dict(self.metadata or {})

    @staticmethod
    def normalize_discovered_from(value: str) -> str:
        value = str(value or "").strip().lower()
        return value if value in DISCOVERY_SOURCES else "manual"

    @staticmethod
    def normalize_source_type(value: str) -> str:
        value = str(value or "").strip().lower()
        return value if value in SOURCE_TYPES else "unknown"

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.replace("www.", "").lower()

    def is_web_url(self) -> bool:
        return urlparse(self.url).scheme.lower() in {"http", "https"} and bool(self.domain)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "discovered_from": self.discovered_from,
            "query": self.query,
            "source_type": self.source_type,
            "priority": self.priority,
            "country_tags": list(self.country_tags),
            "topic_tags": list(self.topic_tags),
            "discovered_at": self.discovered_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UrlCandidate:
        return cls(
            url=data.get("url", ""),
            discovered_from=data.get("discovered_from", "manual"),
            query=data.get("query", ""),
            source_type=data.get("source_type", "unknown"),
            priority=data.get("priority", 50),
            country_tags=data.get("country_tags", []),
            topic_tags=data.get("topic_tags", []),
            discovered_at=data.get("discovered_at") or utc_now_iso(),
            metadata=data.get("metadata", {}),
        )
