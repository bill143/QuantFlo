"""Shared pytest fixtures/markers for QUANTFLO.

``requires_db`` skips a test when Postgres is not reachable (so the non-DB suite
still runs for a dev without the docker stack up, while CI/local-with-containers
run the full suite). The ``pools`` fixture disposes the async engine + Redis pool
inside each test's own event loop (asyncpg connections are loop-bound).
"""
from __future__ import annotations

import socket
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy.engine import make_url

from quantflo.core.config import get_settings


def _db_reachable() -> bool:
    settings = get_settings()
    if not settings.database_url:
        return False
    try:
        url = make_url(settings.database_url)
        with socket.create_connection((url.host or "localhost", url.port or 5432), timeout=2):
            return True
    except Exception:
        return False


def _redis_reachable() -> bool:
    settings = get_settings()
    if not settings.redis_url:
        return False
    try:
        url = urlparse(settings.redis_url)
        with socket.create_connection((url.hostname or "localhost", url.port or 6379), timeout=2):
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(),
    reason="Postgres not reachable — run: docker compose -f infra/docker/docker-compose.yml up -d",
)

requires_redis = pytest.mark.skipif(
    not _redis_reachable(),
    reason="Redis not reachable — run: docker compose -f infra/docker/docker-compose.yml up -d",
)


@pytest_asyncio.fixture
async def pools() -> AsyncIterator[None]:
    """Dispose the process async engine + Redis pool in the test's own loop.

    Each async test gets a fresh event loop; the singleton engine must be disposed
    within the loop that created it to avoid 'Event loop is closed' on the next test.
    """
    yield
    from quantflo.data.db import dispose_engine
    from quantflo.data.redis_client import close_redis

    await dispose_engine()
    await close_redis()
