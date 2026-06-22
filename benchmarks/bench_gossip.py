# [C5-REAL] Exergy-Maximized Benchmark for Gossip Federation Convergence
import asyncio
import time

from cortex.extensions.federation.gossip import GossipNode


async def run_gossip_benchmark(node_count=6):
    print(f"🚀 Initializing Gossip Federation Convergence Benchmark with {node_count} nodes...")

    # 1. Create nodes on dynamic ports
    nodes = [GossipNode(node_id=f"node_{i}", bind_port=0) for i in range(node_count)]

    # Start all nodes
    for node in nodes:
        await node.start()

    try:
        # 2. Setup a sparse overlay network (chain structure) to test transit propagation:
        # node_0 -> node_1 -> node_2 -> ... -> node_(n-1)
        # This requires transit peer discovery to propagate the state end-to-end.
        for i in range(node_count - 1):
            peer_addr = f"127.0.0.1:{nodes[i + 1].bind_port}"
            await nodes[i].register_peer(nodes[i + 1].node_id, peer_addr)
            # Register backward peer as well to ensure bidirectional path
            await nodes[i + 1].register_peer(nodes[i].node_id, f"127.0.0.1:{nodes[i].bind_port}")

        # Inject newer state version into the source node (node_0)
        target_version = 999
        target_facts = 42
        nodes[0].known_state["version"] = target_version
        nodes[0].known_state["facts"] = target_facts

        print("🧬 State injected at node_0. Starting clock for convergence monitoring...")
        t_start = time.perf_counter()

        # 3. Monitor state convergence and peer table discovery
        fully_converged = False
        max_duration = 10.0  # max 10 seconds timeout
        check_interval = 0.05
        elapsed = 0.0

        while elapsed < max_duration:
            # Check if all nodes have learned of target state AND discovered all peers
            states_matching = all(node.known_state["version"] == target_version for node in nodes)
            peers_discovered = all(len(node.peers) >= (node_count - 1) for node in nodes)

            if states_matching and peers_discovered:
                fully_converged = True
                break

            # Manually trigger step propagation to speed up simulation instead of waiting 0.5s ticks
            for node in nodes:
                await node._propagate_state()

            await asyncio.sleep(check_interval)
            elapsed = time.perf_counter() - t_start

        duration_ms = elapsed * 1000.0

        print("\n## Convergence Summary")
        if fully_converged:
            print(
                f"✅ Success: All {node_count} nodes converged to version {target_version} and completed routing tables."
            )
            print(f"- Convergence Latency: {duration_ms:.2f} ms")
        else:
            print("❌ Failure: Did not converge within timeout.")
            for i, node in enumerate(nodes):
                print(
                    f"  Node {i} state: version={node.known_state['version']}, peer_count={len(node.peers)}"
                )

    finally:
        # Stop all nodes
        for node in nodes:
            await node.stop()


if __name__ == "__main__":
    asyncio.run(run_gossip_benchmark())
