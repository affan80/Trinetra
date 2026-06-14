import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.shared.redis_client import ping_redis
from services.shared.redis_dedupe import RedisDedupe
from services.shared.redis_queue import RedisQueue
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_cache import RedisCache
from services.shared.redis_locks import redis_lock
from services.shared.url_frontier import UrlFrontier


def main():
    redis_connected = ping_redis()
    print("Redis connected:", redis_connected)

    if not redis_connected:
        print("Skipping Redis integration checks because Redis is unavailable.")
        return

    dedupe = RedisDedupe()
    print("New URL:", dedupe.is_new_url("https://example.com/test", source="news"))
    print("Same URL again:", dedupe.is_new_url("https://example.com/test", source="news"))

    queue = RedisQueue("raw_items")
    queue.push({
        "title": "Test OSINT item",
        "url": "https://example.com/test",
        "source": "manual",
    })
    print("Queue length:", queue.length())
    print("Popped item:", queue.pop())

    metrics = RedisMetrics()
    metrics.increment("scraped_items")
    metrics.increment_source("news")
    metrics.track_alert("high")
    print("Metrics:", metrics.get_all_metrics())
    print("Source metrics:", metrics.get_all_source_counts())
    print("Risk metrics:", metrics.get_all_risk_counts())

    cache = RedisCache()
    cache.set_json(
        "test_result",
        {
            "score": 91,
            "label": "high_risk",
        },
        ttl_seconds=60,
    )
    print("Cached:", cache.get_json("test_result"))

    with redis_lock("test-job", ttl_seconds=10) as acquired:
        print("Lock acquired:", acquired)

    frontier_queue = RedisQueue("test_url_frontier")
    frontier_queue.clear()
    frontier_queue.clear_dead_letters()
    dedupe.clear_urls(source="test_frontier")
    frontier = UrlFrontier(queue=frontier_queue, dedupe=dedupe)
    first = frontier.enqueue({
        "url": "https://example.com/frontier-test",
        "discovered_from": "test_frontier",
        "source_type": "news",
    })
    second = frontier.enqueue({
        "url": "https://example.com/frontier-test",
        "discovered_from": "test_frontier",
        "source_type": "news",
    })
    print("Frontier first enqueue:", first.reason)
    print("Frontier second enqueue:", second.reason)
    print("Frontier batch:", frontier.dequeue_many(2))

    print("Done")


if __name__ == "__main__":
    main()
