"""Inter-team state bus.

Interface (`StateBus`) plus an in-memory implementation used to share state and
messages between QUANTFLO team agents. No business logic lives here — this is the
transport contract the orchestration layer (Team 5) depends on. A distributed
implementation (e.g. Redis-backed) is a later-phase concern and must satisfy this
same interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True, slots=True)
class BusMessage:
    """A single message published to a topic on the bus."""

    topic: str
    payload: Any
    source: str


Subscriber = Callable[["BusMessage"], None]


class StateBus(ABC):
    """Abstract inter-team state bus contract.

    Two responsibilities, intentionally minimal for Phase 0:
      * key/value state shared across teams (namespaced by team key)
      * publish/subscribe messaging across topics
    """

    @abstractmethod
    def set_state(self, namespace: str, key: str, value: Any) -> None:
        """Store ``value`` under ``namespace``/``key``."""

    @abstractmethod
    def get_state(self, namespace: str, key: str, default: Any = None) -> Any:
        """Return the value at ``namespace``/``key`` or ``default``."""

    @abstractmethod
    def publish(self, message: BusMessage) -> None:
        """Deliver ``message`` to every subscriber of its topic."""

    @abstractmethod
    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        """Register ``subscriber`` to receive messages for ``topic``."""


class InMemoryStateBus(StateBus):
    """Thread-safe, process-local StateBus implementation.

    Suitable for single-process Phase 0 boot and tests.
    """

    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = defaultdict(dict)
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = RLock()

    def set_state(self, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            self._state[namespace][key] = value

    def get_state(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(namespace, {}).get(key, default)

    def publish(self, message: BusMessage) -> None:
        with self._lock:
            subscribers = list(self._subscribers.get(message.topic, ()))
        for subscriber in subscribers:
            subscriber(message)

    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        with self._lock:
            self._subscribers[topic].append(subscriber)
