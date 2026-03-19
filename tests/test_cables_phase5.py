import asyncio
import time

import pytest

from cortex.extensions.swarm.cables import SubmarineCable


@pytest.mark.asyncio
async def test_submarine_cable_priority_multiplexing():
    """Verify that lower priority values (higher urgency) pre-empt others."""
    cable = SubmarineCable(host="127.0.0.1", port=9996, secret=b"secret")
    await cable.initialize()

    client = SubmarineCable(host="127.0.0.1", port=9997, secret=b"secret")
    await client.initialize()

    # Fill with low-priority (high value)
    for i in range(5):
        await client.send("127.0.0.1", 9996, {"id": f"low_{i}"}, priority=9)

    # Send one high-priority (low value)
    await client.send("127.0.0.1", 9996, {"id": "high_0"}, priority=0)

    # First one read MUST be high_0 because PriorityQueue sorts them
    first = await cable.read_next()
    assert first["id"] == "high_0"

    # Then the rest
    for _i in range(5):
        next_msg = await cable.read_next()
        assert next_msg["id"].startswith("low_")

    await client.shutdown()
    await cable.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_compression():
    """Verify that large payloads are compressed and decompressed correctly."""
    cable = SubmarineCable(host="127.0.0.1", port=9995, secret=b"secret")
    await cable.initialize()

    client = SubmarineCable(host="127.0.0.1", port=9994, secret=b"secret")
    await client.initialize()

    # Create a large payload > 1KB
    large_data = "x" * 2048
    payload = {"data": large_data}

    success = await client.send("127.0.0.1", 9995, payload)
    assert success is True

    received = await asyncio.wait_for(cable.read_next(), timeout=2.0)
    assert received == payload

    await client.shutdown()
    await cable.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_circuit_breaker():
    """Verify that failed connections trigger a quarantine period."""
    client = SubmarineCable(host="127.0.0.1", port=9993, secret=b"secret")
    await client.initialize()

    target_host = "127.0.0.1"
    target_port = 12345  # Likely closed

    # First attempt - fails, peer offline, backoff = 2s
    start_time = time.time()
    success1 = await client.send(target_host, target_port, {"ping": 1})
    assert success1 is False

    # Immediate second attempt - should be skipped by circuit breaker
    success2 = await client.send(target_host, target_port, {"ping": 2})
    assert success2 is False
    # Check that it returned quickly (no timeout wait)
    assert time.time() - start_time < 0.5

    await client.shutdown()
