# services/shared/redis_queue.py

from __future__ import annotations

import json
from typing import Any

import redis

from services.shared.redis_client import get_redis_client


class RedisQueue:
    """
    Simple Redis queue using Redis lists.

    Good for:
    - pending URLs
    - raw scraped items
    - alert tasks
    - AI processing jobs

    Commands used:
    - LPUSH for pushing
    - RPOP / BRPOP for consuming
    """

    def __init__(
        self,
        name: str,
        namespace: str = "osint",
        redis_client: redis.Redis | None = None,
    ):
        self.name = name
        self.namespace = namespace
        self.redis = redis_client or get_redis_client()

    @property
    def key(self) -> str:
        return f"{self.namespace}:queue:{self.name}"

    @property
    def dead_letter_key(self) -> str:
        return f"{self.namespace}:queue:{self.name}:dead_letter"

    @staticmethod
    def _serialize(item: dict[str, Any]) -> str:
        return json.dumps(item, ensure_ascii=False)

    @staticmethod
    def _deserialize(raw_item: str | None) -> dict[str, Any] | None:
        if raw_item is None:
            return None

        try:
            return json.loads(raw_item)
        except json.JSONDecodeError:
            return {
                "raw": raw_item,
                "error": "invalid_json",
            }

    def push(self, item: dict[str, Any]) -> int:
        """
        Push one item into queue.
        """

        raw_item = self._serialize(item)
        return int(self.redis.lpush(self.key, raw_item))

    def push_many(self, items: list[dict[str, Any]]) -> int:
        """
        Push multiple items into queue.
        """

        if not items:
            return 0

        raw_items = [self._serialize(item) for item in items]
        return int(self.redis.lpush(self.key, *raw_items))

    def pop(self) -> dict[str, Any] | None:
        """
        Non-blocking pop.
        Returns None if queue is empty.
        """

        raw_item = self.redis.rpop(self.key)
        return self._deserialize(raw_item)

    def blocking_pop(self, timeout: int = 5) -> dict[str, Any] | None:
        """
        Blocking pop.

        timeout=5 means wait max 5 seconds.
        timeout=0 means wait forever.
        """

        result = self.redis.brpop(self.key, timeout=timeout)

        if not result:
            return None

        _, raw_item = result
        return self._deserialize(raw_item)

    def length(self) -> int:
        """
        Queue length.
        """

        return int(self.redis.llen(self.key))

    def peek(self, start: int = 0, end: int = 9) -> list[dict[str, Any]]:
        """
        View queue items without removing them.
        """

        raw_items = self.redis.lrange(self.key, start, end)

        items = []

        for raw_item in raw_items:
            item = self._deserialize(raw_item)
            if item is not None:
                items.append(item)

        return items

    def clear(self) -> int:
        """
        Delete queue.
        """

        return int(self.redis.delete(self.key))

    def move_to_dead_letter(
        self,
        item: dict[str, Any],
        reason: str = "processing_failed",
    ) -> int:
        """
        Move failed item to dead-letter queue.
        """

        failed_item = {
            "reason": reason,
            "item": item,
        }

        raw_item = self._serialize(failed_item)
        return int(self.redis.lpush(self.dead_letter_key, raw_item))

    def dead_letter_length(self) -> int:
        """
        Count failed items.
        """

        return int(self.redis.llen(self.dead_letter_key))

    def get_dead_letters(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get failed items.
        """

        raw_items = self.redis.lrange(self.dead_letter_key, 0, limit - 1)

        items = []

        for raw_item in raw_items:
            item = self._deserialize(raw_item)
            if item is not None:
                items.append(item)

        return items

    def clear_dead_letters(self) -> int:
        """
        Clear dead-letter queue.
        """

        return int(self.redis.delete(self.dead_letter_key))
