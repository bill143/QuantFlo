"""Inter-team state bus package (Team 5 orchestration dependency).

Ships the abstract :class:`StateBus` contract, an :class:`InMemoryStateBus`
(default; used by tests) and a Redis-backed :class:`RedisStateBus` that satisfies
the same interface. ``create_state_bus`` selects a backend.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from quantflo.core.state_bus.bus import (
    BusMessage,
    InMemoryStateBus,
    StateBus,
    Subscriber,
)
from quantflo.core.state_bus.redis_bus import RedisStateBus

if TYPE_CHECKING:
    from quantflo.core.config import Settings

__all__ = [
    "BusMessage",
    "InMemoryStateBus",
    "RedisStateBus",
    "StateBus",
    "Subscriber",
    "create_state_bus",
]


def create_state_bus(backend: str = "memory", settings: Settings | None = None) -> StateBus:
    """Build a state bus: ``"redis"`` -> :class:`RedisStateBus`, else in-memory."""
    if backend == "redis":
        from quantflo.core.config import get_settings

        resolved = settings or get_settings()
        if not resolved.redis_url:
            raise ValueError("redis backend requires QUANTFLO_REDIS_URL")
        return RedisStateBus(resolved.redis_url)
    return InMemoryStateBus()
