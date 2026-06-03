"""Redis-backed StateBus implementation (same interface as the in-memory bus).

State lives in Redis hashes (one per namespace); pub/sub uses a pattern
subscription on ``{prefix}:topic:*`` driven by a background listener thread, so
subscribers can be registered dynamically without touching the connection from
another thread. Values are JSON-serialized (bus payloads must be JSON-serializable
for the distributed transport). No business logic — this is transport only.
"""
from __future__ import annotations

import json
from collections import defaultdict
from threading import RLock
from typing import Any

from redis import Redis

from quantflo.core.state_bus.bus import BusMessage, StateBus, Subscriber


class RedisStateBus(StateBus):
    """Distributed StateBus over Redis (hashes for state, pub/sub for messaging)."""

    def __init__(
        self, redis_url: str, key_prefix: str = "quantflo:bus", client: Redis | None = None
    ) -> None:
        self._client: Redis = client or Redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = RLock()
        self._pubsub: Any = None
        self._listener: Any = None

    def _state_key(self, namespace: str) -> str:
        return f"{self._prefix}:state:{namespace}"

    def _topic_channel(self, topic: str) -> str:
        return f"{self._prefix}:topic:{topic}"

    def set_state(self, namespace: str, key: str, value: Any) -> None:
        self._client.hset(self._state_key(namespace), key, json.dumps(value))

    def get_state(self, namespace: str, key: str, default: Any = None) -> Any:
        raw = self._client.hget(self._state_key(namespace), key)
        return default if raw is None else json.loads(raw)

    def publish(self, message: BusMessage) -> None:
        body = json.dumps(
            {"topic": message.topic, "payload": message.payload, "source": message.source}
        )
        self._client.publish(self._topic_channel(message.topic), body)

    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        with self._lock:
            self._subscribers[topic].append(subscriber)
        self._ensure_listener()

    def _ensure_listener(self) -> None:
        with self._lock:
            if self._pubsub is not None:
                return
            pubsub = self._client.pubsub(ignore_subscribe_messages=True)
            pubsub.psubscribe(**{f"{self._prefix}:topic:*": self._dispatch})
            self._pubsub = pubsub
            self._listener = pubsub.run_in_thread(sleep_time=0.01, daemon=True)

    def _dispatch(self, message: dict[str, Any]) -> None:
        data = json.loads(message["data"])
        bus_message = BusMessage(
            topic=data["topic"], payload=data["payload"], source=data["source"]
        )
        with self._lock:
            callbacks = list(self._subscribers.get(bus_message.topic, ()))
        for callback in callbacks:
            callback(bus_message)

    def close(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join(timeout=2.0)
            self._listener = None
        if self._pubsub is not None:
            self._pubsub.close()
            self._pubsub = None
        self._client.close()
