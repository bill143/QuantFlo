"""In-memory task queue for the QUANTFLO swarm (Phase 0 transport only)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Task:
    """A unit of work routed to a team agent.

    Phase 0 defines the envelope only; handlers are added in later phases.
    """

    task_id: str
    team_key: str
    kind: str
    payload: Any = None


class TaskQueue:
    """FIFO in-memory task queue.

    Minimal by design: enqueue/dequeue/len/is_empty. A durable queue
    (broker-backed) is a later-phase concern and must satisfy this same surface.
    """

    def __init__(self) -> None:
        self._items: deque[Task] = deque()

    def enqueue(self, task: Task) -> None:
        self._items.append(task)

    def dequeue(self) -> Task | None:
        return self._items.popleft() if self._items else None

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return not self._items
