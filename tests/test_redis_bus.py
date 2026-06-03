"""RedisStateBus tests (require a reachable Redis): state round-trip + pub/sub."""
from __future__ import annotations

import time

from quantflo.core.config import get_settings
from quantflo.core.state_bus import BusMessage, RedisStateBus
from tests.conftest import requires_redis

_PREFIX = "quantflo:test:bus"


@requires_redis
def test_redis_state_roundtrip() -> None:
    url = get_settings().redis_url
    assert url
    bus = RedisStateBus(url, key_prefix=_PREFIX)
    try:
        bus.set_state("orchestration", "agent:x", "READY")
        assert bus.get_state("orchestration", "agent:x") == "READY"
        assert bus.get_state("orchestration", "missing", default="d") == "d"
    finally:
        bus.close()


@requires_redis
def test_redis_pubsub_delivery() -> None:
    url = get_settings().redis_url
    assert url
    bus = RedisStateBus(url, key_prefix=_PREFIX)
    received: list[BusMessage] = []
    try:
        bus.subscribe("signals", received.append)
        time.sleep(0.3)  # allow the listener thread to establish the subscription
        bus.publish(BusMessage(topic="signals", payload={"k": 1}, source="researchers"))
        deadline = time.time() + 3.0
        while not received and time.time() < deadline:
            time.sleep(0.05)
        assert len(received) == 1
        assert received[0].payload == {"k": 1}
        assert received[0].source == "researchers"
    finally:
        bus.close()
