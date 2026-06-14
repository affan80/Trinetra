# services/shared/redis_metrics.py

from __future__ import annotations

from typing import Any

import redis

from services.shared.redis_client import get_redis_client


class RedisMetrics:
    """
    Redis metrics helper.

    Good for dashboard counters:
    - scraped items count
    - source-wise count
    - alert count
    - high-risk count
    - worker processed count
    """

    def __init__(
        self,
        namespace: str = "osint",
        redis_client: redis.Redis | None = None,
    ):
        self.namespace = namespace
        self.redis = redis_client or get_redis_client()

    def _metric_key(self) -> str:
        return f"{self.namespace}:metrics:counters"

    def _source_key(self) -> str:
        return f"{self.namespace}:metrics:sources"

    def _risk_key(self) -> str:
        return f"{self.namespace}:metrics:risk"

    def increment(
        self,
        name: str,
        amount: int = 1,
    ) -> int:
        """
        Increment general metric.

        Example:
            scraped_items
            processed_items
            alerts_created
        """

        return int(self.redis.hincrby(self._metric_key(), name, amount))

    def decrement(
        self,
        name: str,
        amount: int = 1,
    ) -> int:
        """
        Decrease general metric.
        """

        return int(self.redis.hincrby(self._metric_key(), name, -amount))

    def get_metric(self, name: str) -> int:
        """
        Get one metric value.
        """

        value = self.redis.hget(self._metric_key(), name)

        if value is None:
            return 0

        return int(value)

    def get_all_metrics(self) -> dict[str, int]:
        """
        Get all general counters.
        """

        data = self.redis.hgetall(self._metric_key())
        return {key: int(value) for key, value in data.items()}

    def increment_source(
        self,
        source: str,
        amount: int = 1,
    ) -> int:
        """
        Count items per source.

        Example:
            rss
            news
            telegram
            reddit
            x
        """

        source = source or "unknown"
        return int(self.redis.hincrby(self._source_key(), source, amount))

    def get_source_count(self, source: str) -> int:
        """
        Get count for one source.
        """

        value = self.redis.hget(self._source_key(), source)

        if value is None:
            return 0

        return int(value)

    def get_all_source_counts(self) -> dict[str, int]:
        """
        Get all source counters.
        """

        data = self.redis.hgetall(self._source_key())
        return {key: int(value) for key, value in data.items()}

    def increment_risk(
        self,
        risk_level: str,
        amount: int = 1,
    ) -> int:
        """
        Count alerts/items by risk.

        Example:
            low
            medium
            high
            critical
        """

        risk_level = risk_level or "unknown"
        return int(self.redis.hincrby(self._risk_key(), risk_level, amount))

    def get_all_risk_counts(self) -> dict[str, int]:
        """
        Get risk counters.
        """

        data = self.redis.hgetall(self._risk_key())
        return {key: int(value) for key, value in data.items()}

    def track_scraped_item(self, item: dict[str, Any]) -> None:
        """
        Track one scraped item.
        """

        source = item.get("source") or item.get("source_type") or "unknown"

        self.increment("scraped_items", 1)
        self.increment_source(source, 1)

    def track_processed_item(self, item: dict[str, Any]) -> None:
        """
        Track one processed item.
        """

        source = item.get("source") or item.get("source_type") or "unknown"

        self.increment("processed_items", 1)
        self.increment_source(source, 1)

    def track_alert(self, risk_level: str = "medium") -> None:
        """
        Track alert creation.
        """

        self.increment("alerts_created", 1)
        self.increment_risk(risk_level, 1)

    def reset_general_metrics(self) -> int:
        """
        Clear general counters.
        """

        return int(self.redis.delete(self._metric_key()))

    def reset_source_metrics(self) -> int:
        """
        Clear source counters.
        """

        return int(self.redis.delete(self._source_key()))

    def reset_risk_metrics(self) -> int:
        """
        Clear risk counters.
        """

        return int(self.redis.delete(self._risk_key()))

    def reset_all(self) -> int:
        """
        Clear all metrics.
        """

        deleted = 0
        deleted += self.reset_general_metrics()
        deleted += self.reset_source_metrics()
        deleted += self.reset_risk_metrics()
        return deleted


metrics = RedisMetrics()


def increment_metric(name: str, amount: int = 1) -> int:
    return metrics.increment(name, amount)


def increment_source_count(source: str, amount: int = 1) -> int:
    return metrics.increment_source(source, amount)


def get_metrics() -> dict[str, Any]:
    return {
        "counters": metrics.get_all_metrics(),
        "sources": metrics.get_all_source_counts(),
        "risk": metrics.get_all_risk_counts(),
    }
