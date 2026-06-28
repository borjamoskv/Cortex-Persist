# [C5-REAL] Exergy-Maximized
"""
Gossip Protocol Stress Test (Epidemic BFT).
Simulates a multi-node Swarm locally on UDP loopback.
Floods the network with events and measures Eventual Consistency convergence time.
"""

import asyncio
import logging
import time

import pytest
from cortex.swarm.gossip_bus import GossipBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.test_gossip_stress")

# Supress excessive debug logging from underlying protocols
logging.getLogger("cortex.federation.gossip").setLevel(logging.WARNING)


async def _spawn_node(node_id: str, port: int) -> GossipBus:
    bus = GossipBus(node_id=node_id, host="127.0.0.1", port=port, sync_interval=0.1)
    await bus.start()
    return bus


@pytest.mark.asyncio
async def test_epidemic_stress():
    """Spawns 5 nodes, interconnects them sparsely, and fires a burst of 100 signals."""
    N_NODES = 5
    BURST_SIZE = 100
    BASE_PORT = 19000

    logger.info(f"🚀 Spawning {N_NODES} GossipBus nodes...")
    nodes: list[GossipBus] = []
    for i in range(N_NODES):
        node = await _spawn_node(f"node_{i}", BASE_PORT + i)
        nodes.append(node)

    # 1. Sparsely connect the network (Node N connects to Node N-1)
    for i in range(1, N_NODES):
        prev_node = nodes[i - 1]
        curr_node = nodes[i]
        await curr_node.node.register_peer(
            prev_node.node_id, f"127.0.0.1:{prev_node.node.bind_port}"
        )
        # Make the connection bidirectional to speed up tests, though gossip handles discovery
        await prev_node.node.register_peer(
            curr_node.node_id, f"127.0.0.1:{curr_node.node.bind_port}"
        )

    await asyncio.sleep(1.0)  # Let them discover and ping

    # 2. Fire burst from Node 0
    logger.info(f"🌊 Firing BURST of {BURST_SIZE} signals from Node 0...")
    t0 = time.monotonic()

    tasks = []
    for i in range(BURST_SIZE):
        tasks.append(nodes[0].broadcast(f"STRESS_TEST_{i}", {"data": "Anergia-Zero", "idx": i}))

    await asyncio.gather(*tasks)
    broadcast_time = (time.monotonic() - t0) * 1000.0
    logger.info(f"⚡ Broadcast completed in {broadcast_time:.2f} ms")

    # 3. Wait for epidemic convergence
    convergence_time = 0.0
    success = False

    logger.info("⏳ Waiting for Epidemic Convergence (Eventual Consistency)...")
    for _ in range(50):  # Max 5 seconds
        await asyncio.sleep(0.1)

        # Check if all nodes have 100 facts known
        all_converged = True
        for node in nodes:
            # We measure facts as versions increments in the node state
            if node.node.known_state["facts"] < BURST_SIZE:
                all_converged = False
                break

        if all_converged:
            success = True
            convergence_time = (time.monotonic() - t0) * 1000.0
            break

    # 4. Cleanup
    for node in nodes:
        await node.stop()

    if success:
        logger.info(f"✅ BFT Convergence Achieved! Time: {convergence_time:.2f} ms")
    else:
        for i, node in enumerate(nodes):
            logger.error(f"Node {i} state: {node.node.known_state}")
        pytest.fail("Epidemic protocol failed to reach consensus within timeout.")


if __name__ == "__main__":
    asyncio.run(test_epidemic_stress())
