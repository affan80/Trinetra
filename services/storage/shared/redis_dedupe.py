# services/shared/redis_dedupe.py

from __future__ import annotations

import hashlib
from urllib.parse import urlparse, urlunparse

import redis
from services.shared.redis_client import get_redis_client


class RedisDedupe:
    """
    Redis-based deduplication helper.

    Use cases:
    - avoid scraping same URL again
    - avoid processing same article text again
    - avoid pushing duplicate social posts
    """

    def __init__(
        self,
        namespace: str = "osint",
        redis_client: redis.Redis | None = None,
    ):
        self.namespace = namespace
        self.redis = redis_client or get_redis_client()

    def _url_key(self, source: str = "global") -> str:
        return f"{self.namespace}:dedupe:urls:{source}"

    def _content_key(self, source: str = "global") -> str:
        return f"{self.namespace}:dedupe:content:{source}"

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL before deduplication.

        Example:
            HTTPS://Example.com/test/#abc
            becomes
            https://example.com/test
        """

        if not url:
            return ""

        url = url.strip()

        parsed = urlparse(url)

        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        query = parsed.query

        normalized = urlunparse(
            (
                scheme,
                netloc,
                path,
                "",
                query,
                "",
            )
        )

        return normalized

    @staticmethod
    def make_hash(value: str) -> str:
        """
        Create SHA256 hash for URL/content.
        """

        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def is_new_url(
        self,
        url: str,
        source: str = "global",
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Returns True if URL is new.
        Returns False if URL was already seen.
        """

        normalized_url = self.normalize_url(url)

        if not normalized_url:
            return False

        url_hash = self.make_hash(normalized_url)
        key = self._url_key(source)

        added = self.redis.sadd(key, url_hash)

        if ttl_seconds:
            self.redis.expire(key, ttl_seconds)

        return added == 1

    def is_seen_url(self, url: str, source: str = "global") -> bool:
        """
        Check if URL already exists in Redis set.
        """

        normalized_url = self.normalize_url(url)

        if not normalized_url:
            return False

        url_hash = self.make_hash(normalized_url)
        key = self._url_key(source)

        return bool(self.redis.sismember(key, url_hash))

    def mark_url_seen(
        self,
        url: str,
        source: str = "global",
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Manually mark URL as seen.
        """

        return self.is_new_url(
            url=url,
            source=source,
            ttl_seconds=ttl_seconds,
        )

    def remove_url(self, url: str, source: str = "global") -> int:
        """
        Remove URL hash from dedupe set.
        """

        normalized_url = self.normalize_url(url)

        if not normalized_url:
            return 0

        url_hash = self.make_hash(normalized_url)
        key = self._url_key(source)

        return int(self.redis.srem(key, url_hash))

    def count_urls(self, source: str = "global") -> int:
        """
        Count unique URLs seen for a source.
        """

        key = self._url_key(source)
        return int(self.redis.scard(key))

    def clear_urls(self, source: str = "global") -> int:
        """
        Delete all URL dedupe data for a source.
        """

        key = self._url_key(source)
        return int(self.redis.delete(key))

    def is_new_content(
        self,
        content: str,
        source: str = "global",
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Deduplicate article text, post body, or extracted content.
        """

        if not content:
            return False

        clean_content = " ".join(content.split()).strip().lower()

        if not clean_content:
            return False

        content_hash = self.make_hash(clean_content)
        key = self._content_key(source)

        added = self.redis.sadd(key, content_hash)

        if ttl_seconds:
            self.redis.expire(key, ttl_seconds)

        return added == 1

    def is_seen_content(self, content: str, source: str = "global") -> bool:
        """
        Check if content already exists in Redis.
        """

        if not content:
            return False

        clean_content = " ".join(content.split()).strip().lower()

        if not clean_content:
            return False

        content_hash = self.make_hash(clean_content)
        key = self._content_key(source)

        return bool(self.redis.sismember(key, content_hash))

    def count_content(self, source: str = "global") -> int:
        """
        Count unique content hashes.
        """

        key = self._content_key(source)
        return int(self.redis.scard(key))

    def clear_content(self, source: str = "global") -> int:
        """
        Clear content dedupe set.
        """

        key = self._content_key(source)
        return int(self.redis.delete(key))
