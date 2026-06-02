"""Tests for the in-memory state bus and task queue (transport, no business logic)."""
from __future__ import annotations

from quantflo.core.state_bus import BusMessage, InMemoryStateBus
from quantflo.orchestration import Task, TaskQueue


def test_state_set_and_get_namespaced() -> None:
    bus = InMemoryStateBus()
    bus.set_state("research", "hypotheses", 3)
    assert bus.get_state("research", "hypotheses") == 3
    assert bus.get_state("research", "missing", default="x") == "x"
    assert bus.get_state("other", "hypotheses") is None


def test_publish_subscribe_delivery() -> None:
    bus = InMemoryStateBus()
    received: list[BusMessage] = []
    bus.subscribe("signals", received.append)
    msg = BusMessage(topic="signals", payload={"k": 1}, source="researchers")
    bus.publish(msg)
    assert received == [msg]


def test_publish_to_topic_without_subscribers_is_noop() -> None:
    bus = InMemoryStateBus()
    bus.publish(BusMessage(topic="empty", payload=None, source="x"))  # must not raise


def test_task_queue_fifo() -> None:
    queue = TaskQueue()
    assert queue.is_empty()
    queue.enqueue(Task(task_id="1", team_key="testers", kind="backtest"))
    queue.enqueue(Task(task_id="2", team_key="testers", kind="backtest"))
    assert len(queue) == 2
    first = queue.dequeue()
    assert first is not None and first.task_id == "1"
    assert queue.dequeue().task_id == "2"  # type: ignore[union-attr]
    assert queue.dequeue() is None
    assert queue.is_empty()
