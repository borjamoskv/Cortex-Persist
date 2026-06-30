import pytest
from babylon60.swarm.router import SwarmRouter, _evaluate_entropy
from babylon60.swarm.registry import AgentRegistry


def test_evaluate_entropy():
    # Low entropy
    req = {"task": "Fix a small typo"}
    assert _evaluate_entropy(req) == 0.1

    # Keyword entropy
    req = {"task": "refactor the memory module"}
    assert _evaluate_entropy(req) == 0.5

    # High entropy (length + keyword)
    req = {
        "task": "Deep architectural refactor of the byzantine consensus engine. This requires touching multiple components and ensuring the ledger is perfectly aligned. Need 100 characters to trigger."
    }
    assert _evaluate_entropy(req) >= 0.8

    # Force quorum
    req = {"task": "simple", "force_quorum": True}
    assert _evaluate_entropy(req) == 1.0


def test_swarm_router_linear_dispatch():
    registry = AgentRegistry()
    registry.register("agent_1")
    registry.register("agent_2")
    registry.register("agent_3")

    router = SwarmRouter(registry)

    req = {"task": "simple task"}
    result = router.route(req)

    assert result["agent_id"] == "agent_1"
    assert result["quorum_agents"] is None
    assert result["entropy_score"] == 0.1


def test_swarm_router_quorum_dispatch():
    registry = AgentRegistry()
    registry.register("agent_1")
    registry.register("agent_2")
    registry.register("agent_3")
    registry.register("agent_4")

    router = SwarmRouter(registry)

    # Task with 'refactor' keyword triggers entropy >= 0.5
    req = {"task": "refactor the module to use Byzantine fault tolerance"}
    result = router.route(req)

    assert result["agent_id"] == "quorum_consensus"
    assert len(result["quorum_agents"]) == 3
    assert result["quorum_agents"] == ["agent_1", "agent_2", "agent_3"]
    assert result["entropy_score"] >= 0.5
