from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.scraper.discovery import UrlCandidate
from services.scraper.policy import SourcePolicy
from services.shared.redis_dedupe import RedisDedupe
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_queue import RedisQueue

FRONTIER_METRICS = {
    "discovered": "discovery_candidates",
    "enqueued": "frontier_enqueued",
    "duplicate": "frontier_duplicates",
    "rejected": "frontier_policy_rejections",
    "dequeued": "frontier_dequeued",
    "dead_letter": "frontier_dead_letters",
}


@dataclass
class FrontierResult:
    accepted: bool
    reason: str
    candidate: dict[str, Any] | None = None


class UrlFrontier:
    def __init__(
        self,
        queue: RedisQueue | None = None,
        dedupe: RedisDedupe | None = None,
        policy: SourcePolicy | None = None,
        metrics: RedisMetrics | None = None,
        queue_name: str = "url_frontier",
    ):
        self.queue = queue or RedisQueue(queue_name)
        self.dedupe = dedupe or RedisDedupe()
        self.policy = policy or SourcePolicy()
        self.metrics = metrics

    def enqueue(self, candidate: UrlCandidate | dict, ttl_seconds: int | None = None) -> FrontierResult:
        candidate = self.normalize_candidate(candidate)

        if not candidate.is_web_url():
            self.track(FRONTIER_METRICS["rejected"])
            return FrontierResult(False, "invalid_web_url", candidate.to_dict())

        if not self.policy.is_allowed(candidate.url):
            self.track(FRONTIER_METRICS["rejected"])
            return FrontierResult(False, "source_policy_rejected", candidate.to_dict())

        dedupe_source = candidate.discovered_from or "frontier"
        if not self.dedupe.is_new_url(candidate.url, source=dedupe_source, ttl_seconds=ttl_seconds):
            self.track(FRONTIER_METRICS["duplicate"])
            return FrontierResult(False, "duplicate_url", candidate.to_dict())

        payload = candidate.to_dict()
        self.queue.push(payload)
        self.track(FRONTIER_METRICS["enqueued"])
        return FrontierResult(True, "enqueued", payload)

    def enqueue_many(self, candidates: list[UrlCandidate | dict], ttl_seconds: int | None = None) -> list[FrontierResult]:
        return [self.enqueue(candidate, ttl_seconds=ttl_seconds) for candidate in candidates]

    def dequeue(self) -> dict[str, Any] | None:
        item = self.queue.pop()
        if item:
            self.track(FRONTIER_METRICS["dequeued"])
        return item

    def blocking_dequeue(self, timeout: int = 5) -> dict[str, Any] | None:
        item = self.queue.blocking_pop(timeout=timeout)
        if item:
            self.track(FRONTIER_METRICS["dequeued"])
        return item

    def dequeue_many(self, limit: int = 10) -> list[dict[str, Any]]:
        items = []

        for _ in range(max(0, limit)):
            item = self.dequeue()
            if not item:
                break
            items.append(item)

        return items

    def length(self) -> int:
        return self.queue.length()

    def move_to_dead_letter(self, candidate: dict[str, Any], reason: str = "crawl_failed") -> int:
        self.track(FRONTIER_METRICS["dead_letter"])
        return self.queue.move_to_dead_letter(candidate, reason=reason)

    def dead_letter_length(self) -> int:
        return self.queue.dead_letter_length()

    def get_dead_letters(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.queue.get_dead_letters(limit=limit)

    def stats(self) -> dict[str, Any]:
        return {
            "queue_name": self.queue.name,
            "queue_key": self.queue.key,
            "queue_length": self.length(),
            "dead_letter_length": self.dead_letter_length(),
        }

    @staticmethod
    def normalize_candidate(candidate: UrlCandidate | dict) -> UrlCandidate:
        if isinstance(candidate, UrlCandidate):
            return UrlCandidate.from_dict(candidate.to_dict())

        return UrlCandidate.from_dict(candidate)

    def track(self, name: str) -> None:
        if not self.metrics:
            return

        try:
            self.metrics.increment(name)
        except Exception:
            pass
