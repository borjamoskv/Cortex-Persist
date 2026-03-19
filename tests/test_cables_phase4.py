import asyncio
import os
import unittest.mock as mock

import pytest

from cortex.extensions.swarm.cables import SubmarineCable
from cortex.extensions.swarm.swarm_heartbeat import SWARM_HEARTBEAT


@pytest.mark.asyncio
async def test_submarine_cable_uds_transport():
    """Verify Unix Domain Socket transport."""
    socket_path = "/tmp/test_cables.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)

    # Server on UDS
    server_cable = SubmarineCable(host=socket_path, secret=b"secret")
    await server_cable.initialize()

    # Client sending to UDS
    client_cable = SubmarineCable(secret=b"secret")
    await client_cable.initialize()

    payload = {"type": "uds_test", "data": 123}
    success = await client_cable.send(socket_path, "uds", payload)
    assert success is True

    # Verify receipt
    received = await asyncio.wait_for(server_cable.read_next(), timeout=2.0)
    assert received == payload

    await client_cable.shutdown()
    await server_cable.shutdown()
    if os.path.exists(socket_path):
        os.remove(socket_path)


@pytest.mark.asyncio
async def test_submarine_cable_deduplication():
    """Verify that identical payloads are suppressed."""
    cable = SubmarineCable(host="127.0.0.1", port=9998, secret=b"secret")
    await cable.initialize()

    client = SubmarineCable(secret=b"secret")
    await client.initialize()

    payload = {"repeat": "me"}

    # First send - should transmit
    await client.send("127.0.0.1", 9998, payload)
    received1 = await asyncio.wait_for(cable.read_next(), timeout=2.0)
    assert received1 == payload

    # Second send (identical) - should be suppressed
    # We check if anything arrives at the server. It shouldn't.
    await client.send("127.0.0.1", 9998, payload)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(cable.read_next(), timeout=0.5)

    # Third send (different) - should transmit
    payload2 = {"repeat": "me", "diff": True}
    await client.send("127.0.0.1", 9998, payload2)
    received2 = await asyncio.wait_for(cable.read_next(), timeout=2.0)
    assert received2 == payload2

    await client.shutdown()
    await cable.shutdown()


@pytest.mark.asyncio
async def test_submarine_cable_heartbeat_integration():
    """Verify SWARM_HEARTBEAT.pulse is called on receiving data."""
    with mock.patch.object(SWARM_HEARTBEAT, "pulse") as mock_pulse:
        cable = SubmarineCable(host="127.0.0.1", port=9997, secret=b"secret")
        await cable.initialize()

        client = SubmarineCable(secret=b"secret")
        await client.initialize()

        await client.send("127.0.0.1", 9997, {"ping": "pong"})
        await cable.read_next()

        assert mock_pulse.called
        assert mock_pulse.call_args[0][0] == "submarine_cable"

        await client.shutdown()
        await cable.shutdown()
