# [C5-REAL] Exergy-Maximized
"""
Tests for the Distributed Event Bus.
Verifies local RAM fallback, callback dispatching, and mock Redis Streams integration.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from babylon60.events.bus import DistributedEventBus


@pytest.mark.asyncio
async def test_event_bus_local_fallback_dispatch():
    """Verify that when Redis is unavailable, the bus falls back to local RAM dispatch."""
    bus = DistributedEventBus(redis_url=None)

    received_payloads = []

    async def callback(payload):
        received_payloads.append(payload)

    bus.subscribe("test.topic", callback)

    test_payload = {"source": "test_suite", "message": "hello"}
    await bus.publish("test.topic", test_payload)

    # Allow async loop to settle
    await asyncio.sleep(0.05)

    assert len(received_payloads) == 1
    assert received_payloads[0] == test_payload
    await bus.shutdown()


@pytest.mark.asyncio
async def test_event_bus_redis_stream_publishing():
    """Verify that when Redis is active, events are published using xadd."""
    mock_redis = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        # We explicitly pass a url to trigger Redis connection path
        bus = DistributedEventBus(redis_url="redis://localhost:6379")
        assert bus._redis is mock_redis

        test_payload = {"key": "value"}
        await bus.publish("swarm.event", test_payload)

        # Verify xadd called with maxlen 1000 and JSON payload
        mock_redis.xadd.assert_called_once()
        args, kwargs = mock_redis.xadd.call_args
        assert args[0] == "cortex:stream:swarm.event"
        assert "payload" in args[1]
        assert "value" in args[1]["payload"]
        assert kwargs.get("maxlen") == 1000
        await bus.shutdown()


@pytest.mark.asyncio
async def test_event_bus_redis_stream_subscriber_worker():
    """Verify that subscribing triggers background xread worker task and updates callbacks."""
    mock_redis = AsyncMock()
    mock_redis.xinfo_stream.side_effect = Exception("No stream yet")

    # Simulate a single stream message yield, then block/exit
    future_data = [
        [("cortex:stream:swarm.update", [("12345-0", {"payload": '{"event": "alert"}'})])]
    ]

    async def mock_xread(*args, **kwargs):
        if future_data:
            await asyncio.sleep(0.01)
            return future_data.pop(0)
        # Block indefinitely to simulate empty stream
        await asyncio.sleep(5)
        return []

    mock_redis.xread.side_effect = mock_xread

    received_alerts = []

    async def alert_callback(payload):
        received_alerts.append(payload)

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        bus = DistributedEventBus(redis_url="redis://localhost:6379")

        bus.subscribe("swarm.update", alert_callback)
        assert len(bus._redis_tasks) == 1

        # Give background listener task time to read and dispatch the mocked message
        await asyncio.sleep(0.1)

        assert len(received_alerts) == 1
        assert received_alerts[0] == {"event": "alert"}

        await bus.shutdown()
