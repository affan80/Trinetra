# services/shared/redis_cache.py

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

import redis
from services.shared.redis_client import get_redis_client


class RedisCache:
    """
    Redis cache helper.

    Use cases:
    - cache article extraction result
    - cache credibility score
    - cache AI model output
    - cache API response
    """

    def __init__(
        self,
        namespace: str = "osint",
        redis_client: redis.Redis | None = None,
    ):
        self.namespace = namespace
        self.redis = redis_client or get_redis_client()

    def make_key(self, key: str) -> str:
        """
        Create namespaced cache key.
        """

        return f"{self.namespace}:cache:{key}"

    @staticmethod
    def make_hash_key(value: str) -> str:
        """
        Create safe hash key from long value.

        Useful for:
            URL
            long article text
            query
        """

        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = 3600,
    ) -> bool:
        """
        Set plain string cache.
        """

        full_key = self.make_key(key)

        result = self.redis.set(
            name=full_key,
            value=value,
            ex=ttl_seconds,
        )

        return bool(result)

    def get(self, key: str) -> str | None:
        """
        Get plain string cache.
        """

        full_key = self.make_key(key)
        return self.redis.get(full_key)

    def set_json(
        self,
        key: str,
        value: dict[str, Any] | list[Any],
        ttl_seconds: int | None = 3600,
    ) -> bool:
        """
        Store JSON value.
        """

        full_key = self.make_key(key)

        raw_value = json.dumps(
            value,
            ensure_ascii=False,
        )

        result = self.redis.set(
            name=full_key,
            value=raw_value,
            ex=ttl_seconds,
        )

        return bool(result)

    def get_json(
        self,
        key: str,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Get JSON value.
        """

        full_key = self.make_key(key)
        raw_value = self.redis.get(full_key)

        if raw_value is None:
            return None

        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return None

    def exists(self, key: str) -> bool:
        """
        Check if cache key exists.
        """

        full_key = self.make_key(key)
        return bool(self.redis.exists(full_key))

    def delete(self, key: str) -> int:
        """
        Delete cache key.
        """

        full_key = self.make_key(key)
        return int(self.redis.delete(full_key))

    def ttl(self, key: str) -> int:
        """
        Get TTL.

        -2 means key does not exist.
        -1 means key exists but has no expiry.
        """

        full_key = self.make_key(key)
        return int(self.redis.ttl(full_key))

    def get_or_set_json(
        self,
        key: str,
        factory: Callable[[], dict[str, Any] | list[Any]],
        ttl_seconds: int | None = 3600,
    ) -> dict[str, Any] | list[Any]:
        """
        Get cached JSON.
        If not available, call factory function and cache result.

        Example:
            result = cache.get_or_set_json(
                key="article_score:123",
                factory=lambda: run_ai_model(article),
                ttl_seconds=3600
            )
        """

        cached_value = self.get_json(key)

        if cached_value is not None:
            return cached_value

        fresh_value = factory()

        self.set_json(
            key=key,
            value=fresh_value,
            ttl_seconds=ttl_seconds,
        )

        return fresh_value

    def cache_article_result(
        self,
        article_url: str,
        result: dict[str, Any],
        ttl_seconds: int | None = 86400,
    ) -> bool:
        """
        Cache result for one article URL.
        """

        url_hash = self.make_hash_key(article_url)
        key = f"article:{url_hash}"

        return self.set_json(
            key=key,
            value=result,
            ttl_seconds=ttl_seconds,
        )

    def get_article_result(
        self,
        article_url: str,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Get cached article result.
        """

        url_hash = self.make_hash_key(article_url)
        key = f"article:{url_hash}"

        return self.get_json(key)

    def clear_by_pattern(
        self,
        pattern: str,
        batch_size: int = 100,
    ) -> int:
        """
        Delete keys by pattern.

        Example:
            clear_by_pattern("article:*")

        This uses SCAN, safer than KEYS.
        """

        full_pattern = self.make_key(pattern)

        deleted = 0

        for key in self.redis.scan_iter(
            match=full_pattern,
            count=batch_size,
        ):
            deleted += int(self.redis.delete(key))

        return deleted
