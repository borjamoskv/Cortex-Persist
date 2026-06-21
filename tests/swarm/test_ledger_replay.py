import pytest
from cortex.swarm.router import SwarmRouter
from cortex.swarm.registry import AgentRegistry


@pytest.fixture
def router() -> SwarmRouter:
    registry = AgentRegistry()
    registry.register("memory", capabilities=["read", "write"])
    registry.register("oracle", capabilities=["audit", "analyze"])
    return SwarmRouter(registry=registry)


def test_swarm_replay_consistency(router):
    """Critical: identical inputs must produce identical event signatures."""
    req = {"task": "audit memory consistency", "context": {"tenant": "x"}}

    a = router.route(req)
    b = router.route(req)

    assert a == b, "Routing must be deterministic for identical inputs"

    events = router.ledger.replay("audit memory consistency")
    assert len(events) >= 2

    # Verify deterministic_signature is consistent across identical inputs
    sigs = [e["deterministic_signature"] for e in events]
    assert len(set(sigs)) == 1, "All replay events for same input must share signature"
