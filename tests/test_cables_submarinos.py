import asyncio
import json

import pytest

from cortex.extensions.swarm.cables import SubmarineCable


@pytest.mark.asyncio
async def test_submarine_cable_init_and_shutdown():
    cable = SubmarineCable(port=9998)
    await cable.initialize()
    status = cable.get_status()
    assert status["status"] == "active"
    assert status["inbox_size"] == 0
    await cable.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_transmission():
    server = SubmarineCable(port=9997)
    await server.initialize()

    client = SubmarineCable()

    # Send a valid message
    success = await client.send("127.0.0.1", 9997, {"action": "sync", "data": 42})
    assert success is True

    # Read the message with a timeout
    msg = await asyncio.wait_for(server.read_next(), timeout=2.0)
    assert msg == {"action": "sync", "data": 42}

    await server.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_invalid_signature():
    server = SubmarineCable(port=9996)
    await server.initialize()

    # Send a forged message by opening a raw connection
    reader, writer = await asyncio.open_connection("127.0.0.1", 9996)
    forged_payload = {"action": "hack"}
    # Bad signature
    msg = {"payload": forged_payload, "sig": "badsignature123"}

    writer.write(json.dumps(msg).encode("utf-8") + b"\n")
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    # Wait a small moment for async events
    await asyncio.sleep(0.1)

    # The inbox should be empty because the forged message was dropped
    assert server._inbox.empty()
    assert server.get_status()["inbox_size"] == 0

    await server.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_eviction():
    cable = SubmarineCable(port=9995)
    await cable.initialize()

    # Manually fill the inbox
    await cable._inbox.put({"test": 1})
    await cable._inbox.put({"test": 2})

    assert cable.get_status()["inbox_size"] == 2

    evicted = cable.evict_stale_data()
    assert evicted == 2
    assert cable.get_status()["inbox_size"] == 0

    await cable.shutdown()
