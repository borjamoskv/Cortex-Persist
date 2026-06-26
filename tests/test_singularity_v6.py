# [C5-REAL] Exergy-Maximized
import pytest

from cortex.engine.swarm_10k import CenturionSuperv
from cortex_extensions.llm._cascade import CascadeManager, IntentProfile
from cortex_extensions.signals.sharded_bus import ShardedAsyncSignalBus


@pytest.mark.asyncio
async def test_exergy_calculation_o1(tmp_path):
    """Verify the Nine Laws - Exergy decay on latency/density."""
    bus = ShardedAsyncSignalBus(base_dir=tmp_path)
    node = CenturionSuperv("node-1", "test_shard_bus_1")

    # Initial state: 1.0 exergy
    ex = await node.get_exergy()
    assert ex == 1.0

    # Simulating 50% density
    for i in range(50):
        node.agents.append(f"ag-{i}")
    node.metrics.active_children = len(node.agents)

    # Simulating 32ms latency (Double the 16ms threshold)
    node.last_latency_ms = 32.0

    ex = await node.get_exergy()
    # Density factor = 0.5
    # Latency factor = exp(-(32-16)/32) = exp(-0.5) approx 0.606
    # Expected approx 0.303
    assert 0.30 <= ex <= 0.31

    await bus.close()


class MockProvider:
    def __init__(self, name, affinity=IntentProfile.REASONING):
        self.provider_name = name
        self.intent_affinity = affinity


@pytest.mark.asyncio
async def test_kv_aware_routing_affinity():
    """Verify Corolario AX-IV - Routing sticks to warm KV instances."""
    mgr = CascadeManager()
    p1 = MockProvider("p1")
    p2 = MockProvider("p2")

    # Register success but higher latency for p1
    mgr.set_a_record("p1", 100.0)
    mgr.set_a_record("p2", 50.0)

    # Without affinity, p2 (lower latency) should be first
    ordered = mgr.promote_known_good([p1, p2], IntentProfile.REASONING)
    assert ordered[0].provider_name == "p2"

    # Mark KV affinity for p1
    mgr.set_kv_affinity("p1", "hash-123")

    # With affinity for hash-123, p1 should be promoted even with higher latency
    ordered_affinity = mgr.promote_known_good(
        [p1, p2], IntentProfile.REASONING, prefix_hash="hash-123"
    )
    assert ordered_affinity[0].provider_name == "p1"
    assert ordered_affinity[1].provider_name == "p2"
