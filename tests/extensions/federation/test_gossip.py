# [C5-REAL] Exergy-Maximized
import asyncio
import pytest
from cortex.extensions.federation.gossip import GossipNode


@pytest.mark.asyncio
async def test_gossip_node_communication_and_discovery() -> None:
    # 1. Initialize two nodes on different ports
    node_a = GossipNode(node_id="node_a", bind_port=0)
    node_b = GossipNode(node_id="node_b", bind_port=0)

    # Modify state of Node A to simulate a newer version / fact injection
    node_a.known_state["version"] = 42
    node_a.known_state["facts"] = 10

    # Start both nodes
    await node_a.start()
    await node_b.start()

    try:
        # Register Node B in Node A's table
        await node_a.register_peer("node_b", f"127.0.0.1:{node_b.bind_port}")

        # Give the event loop a moment to propagate
        # We manually trigger state propagation on Node A to send a PING to Node B
        await node_a._propagate_state()

        # Wait up to 1 second for the datagram and processing to happen
        for _ in range(20):
            if "node_a" in node_b.peers and node_b.known_state["version"] == 42:
                break
            await asyncio.sleep(0.05)

        # 2. Check that Node B successfully discovered Node A
        assert "node_a" in node_b.peers
        assert node_b.peers["node_a"]["address"] == f"127.0.0.1:{node_a.bind_port}"

        # 3. Check that Node B successfully merged Node A's newer state
        assert node_b.known_state["version"] == 42
        assert node_b.known_state["facts"] == 10
        assert "vitals" in node_b.peers["node_a"]

        # Now check transit discovery: Initialize Node C, register only A in C
        node_c = GossipNode(node_id="node_c", bind_port=0)
        await node_c.start()
        try:
            await node_c.register_peer("node_a", f"127.0.0.1:{node_a.bind_port}")
            # Trigger propagation from Node C to Node A. Node C has node_a.
            # Node A knows about node_b. Through datagram exchanges, Node C should learn about node_b.
            await node_c._propagate_state()

            # Wait for Node C to learn about Node B from Node A's peer list
            for _ in range(20):
                if "node_b" in node_c.peers:
                    break
                await asyncio.sleep(0.05)

            assert "node_b" in node_c.peers
            assert node_c.peers["node_b"]["address"] == f"127.0.0.1:{node_b.bind_port}"

        finally:
            await node_c.stop()

    finally:
        await node_a.stop()
        await node_b.stop()
