# services/shared/redis_locks.py

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

import redis

from services.shared.redis_client import get_redis_client


class RedisLockManager:
    """
    Redis distributed lock helper.

    Use cases:
    - only one worker processes same article
    - avoid duplicate AI model processing
    - avoid duplicate alert generation
    """

    def __init__(
        self,
        namespace: str = "osint",
        redis_client: redis.Redis | None = None,
    ):
        self.namespace = namespace
        self.redis = redis_client or get_redis_client()

    def _lock_key(self, name: str) -> str:
        return f"{self.namespace}:lock:{name}"

    def acquire_lock(
        self,
        name: str,
        ttl_seconds: int = 30,
        blocking: bool = False,
        blocking_timeout: int | None = None,
    ) -> redis.lock.Lock | None:
        """
        Acquire Redis lock.

        ttl_seconds:
            Lock auto-expires after this time.

        blocking=False:
            If lock exists, return None immediately.

        blocking=True:
            Wait until lock is available.
        """

        lock = self.redis.lock(
            name=self._lock_key(name),
            timeout=ttl_seconds,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

        acquired = lock.acquire()

        if acquired:
            return lock

        return None

    def release_lock(self, lock: redis.lock.Lock | None) -> bool:
        """
        Release lock safely.
        """

        if lock is None:
            return False

        try:
            lock.release()
            return True
        except redis.exceptions.LockError:
            return False

    def is_locked(self, name: str) -> bool:
        """
        Check if lock exists.
        """

        key = self._lock_key(name)
        return bool(self.redis.exists(key))

    def force_unlock(self, name: str) -> int:
        """
        Force delete lock.

        Use carefully.
        """

        key = self._lock_key(name)
        return int(self.redis.delete(key))


@contextmanager
def redis_lock(
    name: str,
    ttl_seconds: int = 30,
    namespace: str = "osint",
    blocking: bool = False,
    blocking_timeout: int | None = None,
) -> Iterator[bool]:
    """
    Context manager for Redis lock.

    Example:
        with redis_lock("article:123") as acquired:
            if not acquired:
                return
            process_article()
    """

    manager = RedisLockManager(namespace=namespace)

    lock = manager.acquire_lock(
        name=name,
        ttl_seconds=ttl_seconds,
        blocking=blocking,
        blocking_timeout=blocking_timeout,
    )

    acquired = lock is not None

    try:
        yield acquired
    finally:
        if acquired:
            manager.release_lock(lock)


def wait_for_lock_release(
    name: str,
    namespace: str = "osint",
    timeout_seconds: int = 10,
    check_interval: float = 0.2,
) -> bool:
    """
    Wait until lock is released.

    Returns True if lock released.
    Returns False if timeout reached.
    """

    manager = RedisLockManager(namespace=namespace)

    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        if not manager.is_locked(name):
            return True

        time.sleep(check_interval)

    return False
