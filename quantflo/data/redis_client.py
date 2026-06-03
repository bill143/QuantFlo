"""Async Redis connection pool for QUANTFLO (state-bus cache + hot state)."""
from __future__ import annotations

import redis.asyncio as redis

from quantflo.core.config import get_settings

_pool: redis.ConnectionPool | None = None


def get_redis() -> redis.Redis:
    """Return a Redis client bound to the process-wide connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        if not settings.redis_url:
            raise RuntimeError("QUANTFLO_REDIS_URL is not set")
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=False,
        )
    return redis.Redis(connection_pool=_pool)


async def close_redis() -> None:
    """Close the Redis pool (call on shutdown / between test runs)."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
    _pool = None
