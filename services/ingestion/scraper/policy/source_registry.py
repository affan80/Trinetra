from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

from services.scraper.discovery import UrlCandidate

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_REGISTRY_PATH = os.getenv(
    "SOURCE_REGISTRY_PATH",
    os.path.join(PROJECT_ROOT, "config", "scraper", "source_registry.json"),
)


def merge_tags(existing: list[str], additions: list[str]) -> list[str]:
    tags = []
    seen = set()

    for tag in [*existing, *additions]:
        text = str(tag).strip()
        key = text.lower()

        if text and key not in seen:
            seen.add(key)
            tags.append(text)

    return tags


@dataclass
class SourceRegistryEntry:
    source_name: str
    source_type: str = "unknown"
    base_url: str = ""
    platform_id: str = ""
    enabled: bool = True
    priority: int = 50
    country_tags: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    rss_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    discovery_queries: list[str] = field(default_factory=list)
    common_crawl_patterns: list[str] = field(default_factory=list)
    reddit_subreddits: list[str] = field(default_factory=list)
    youtube_queries: list[str] = field(default_factory=list)
    telegram_channels: list[str] = field(default_factory=list)
    allow_paths: list[str] = field(default_factory=list)
    deny_paths: list[str] = field(default_factory=list)
    robots_obey: bool = True
    max_depth: int = 2
    max_pages: int = 100
    download_delay: float = 1.0
    scrapling_fallback_allowed: bool = False

    @property
    def domain(self) -> str:
        return urlparse(self.base_url).netloc.replace("www.", "").lower()

    def matches_url(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").lower()
        path = parsed.path or "/"

        if not self.domain or not (domain == self.domain or domain.endswith("." + self.domain)):
            return False

        if self.deny_paths and any(path.startswith(deny) for deny in self.deny_paths):
            return False

        if self.allow_paths:
            return any(path.startswith(allow) for allow in self.allow_paths)

        return True

    def to_policy_metadata(self) -> dict:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "robots_obey": self.robots_obey,
            "max_depth": self.max_depth,
            "max_pages": self.max_pages,
            "download_delay": self.download_delay,
            "scrapling_fallback_allowed": self.scrapling_fallback_allowed,
        }


class SourceRegistry:
    def __init__(self, entries: list[SourceRegistryEntry] | None = None):
        self.entries = entries or []

    def add(self, entry: SourceRegistryEntry) -> None:
        entry = self.validate_entry(entry)
        self.entries.append(entry)

    @property
    def enabled_entries(self) -> list[SourceRegistryEntry]:
        return [entry for entry in self.entries if entry.enabled]

    def find_for_url(self, url: str) -> SourceRegistryEntry | None:
        for entry in self.enabled_entries:
            if entry.matches_url(url):
                return entry

        return None

    def enrich_candidate(self, candidate: UrlCandidate | dict) -> UrlCandidate:
        if isinstance(candidate, dict):
            candidate = UrlCandidate.from_dict(candidate)

        entry = self.find_for_url(candidate.url)
        if not entry:
            return candidate

        if candidate.source_type == "unknown":
            candidate.source_type = UrlCandidate.normalize_source_type(entry.source_type)

        if candidate.priority == 50:
            candidate.priority = max(0, min(int(entry.priority), 100))

        candidate.country_tags = merge_tags(candidate.country_tags, entry.country_tags)
        candidate.topic_tags = merge_tags(candidate.topic_tags, entry.topic_tags)

        metadata = dict(candidate.metadata)
        metadata.setdefault("source_registry", entry.to_policy_metadata())
        candidate.metadata = metadata

        return candidate

    @classmethod
    def from_dicts(cls, entries: list[dict]) -> "SourceRegistry":
        return cls([cls.validate_entry(SourceRegistryEntry(**entry)) for entry in entries])

    @classmethod
    def from_file(cls, path: str | None = None) -> "SourceRegistry":
        path = path or DEFAULT_REGISTRY_PATH

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            entries = data.get("sources", [])
        else:
            entries = data

        if not isinstance(entries, list):
            raise ValueError("Source registry must contain a list of sources")

        return cls.from_dicts(entries)

    @staticmethod
    def validate_entry(entry: SourceRegistryEntry) -> SourceRegistryEntry:
        if not entry.source_name:
            raise ValueError("Source registry entry requires source_name")

        if not entry.base_url and not entry.platform_id:
            has_discovery_source = any([
                entry.rss_urls,
                entry.sitemap_urls,
                entry.discovery_queries,
                entry.reddit_subreddits,
                entry.youtube_queries,
                entry.telegram_channels,
            ])
            if not has_discovery_source:
                raise ValueError(f"Source registry entry {entry.source_name} needs a base_url, platform_id, or discovery source")

        entry.priority = max(0, min(int(entry.priority), 100))
        return entry
