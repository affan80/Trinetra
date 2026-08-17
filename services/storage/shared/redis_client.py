# services/shared/redis_client.py

from __future__ import annotations

import os
from functools import lru_cache

import redis
from dotenv import load_dotenv


load_dotenv()


DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """
    Creates one reusable Redis client for the whole app.

    Local:
        REDIS_URL=redis://localhost:6379/0

    Docker Compose:
        REDIS_URL=redis://redis:6379/0
    """

    redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)

    client = redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30,
    )

    return client


def ping_redis() -> bool:
    """
    Check Redis connection.
    """

    try:
        client = get_redis_client()
        return bool(client.ping())
    except redis.RedisError:
        return False


def get_redis_url() -> str:
    """
    Return active Redis URL.
    Useful for debugging.
    """

    return os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
