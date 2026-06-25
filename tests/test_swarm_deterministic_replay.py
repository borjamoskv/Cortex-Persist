"""
tests/test_swarm_deterministic_replay.py

Deterministic replay tests for SwarmRouter V2.

Tests 4 invariants:
1. routing is pure function: same input => same output same instance
2. routing stable across instances: same registry state => same output
3. JSON round-trip stability (snapshot contract)
4. routing_hash stability: byte-identical hash across runs

Edge cases covered:
- unknown task (no keyword match) => fallback to all agents sorted
- single agent registry
- registry order independence (sorted keys)
"""
import hashlib
import json

import pytest

from cortex.swarm.router import SwarmRouter
from cortex.swarm.registry import AgentRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash(obj: dict) -> str:
    """Stable SHA256 for deterministic comparison."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _make_registry() -> AgentRegistry:
    """Canonical test registry (3 agents, deterministic caps)."""
    registry = AgentRegistry()
    registry.register("memory", capabilities=["read", "write"])
    registry.register("oracle", capabilities=["audit", "analyze"])
    registry.register("worker", capabilities=["compute", "transform"])
    return registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def router() -> SwarmRouter:
    return SwarmRouter(registry=_make_registry())


# ---------------------------------------------------------------------------
# Core invariant tests
# ---------------------------------------------------------------------------

def test_swarm_routing_is_deterministic(router: SwarmRouter) -> None:
    """Invariant 1: pure function — same instance, same input => identical output."""
    request = {
        "task": "analyze ledger anomalies",
        "context": {
            "priority": "high",
            "tenant_id": "test-tenant",
        },
    }

    out1 = router.route(request)
    out2 = router.route(request)

    assert out1 == out2
    # deep stability guard: byte-identical hash
    assert _hash(out1) == _hash(out2)


def test_swarm_replay_across_instances() -> None:
    """Invariant 2: across instances — same registry state => same output."""
    registry = _make_registry()

    request = {
        "task": "audit memory consistency",
        "context": {"tenant_id": "replay-test"},
    }

    r1 = SwarmRouter(registry=registry).route(request)
    r2 = SwarmRouter(registry=registry).route(request)

    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_routing_hash_is_stable(router: SwarmRouter) -> None:
    """routing_hash must be byte-identical across calls."""
    request = {"task": "compute transform", "context": {"seed": 42}}

    h1 = router.route(request)["routing_hash"]
    h2 = router.route(request)["routing_hash"]

    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


# ---------------------------------------------------------------------------
# Ledger-grade snapshot fixture
# ---------------------------------------------------------------------------

def test_swarm_replay_snapshot(router: SwarmRouter) -> None:
    """
    Snapshot contract: output must survive JSON round-trip unchanged.

    This validates:
    - all values are JSON-serializable
    - no floats, timestamps, or non-stable types in output
    - snapshot is self-consistent after sort_keys serialization
    """
    request = {"task": "compute x", "context": {"seed": 42}}

    output = router.route(request)

    snapshot = {
        "input": request,
        "output": output,
    }

    assert snapshot == json.loads(json.dumps(snapshot, sort_keys=True))


def test_registry_checksum_is_stable() -> None:
    """Registry checksum must be identical for same state."""
    r1 = SwarmRouter(registry=_make_registry())
    r2 = SwarmRouter(registry=_make_registry())

    assert r1.registry_checksum() == r2.registry_checksum()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_unknown_task_fallback_is_deterministic(router: SwarmRouter) -> None:
    """
    Edge: task with no keyword match must fallback to ALL agents sorted.
    Fallback must also be deterministic.
    """
    request = {"task": "xyzzy unknown gibberish", "context": {}}

    out1 = router.route(request)
    out2 = router.route(request)

    assert out1 == out2
    # fallback: all agents present
    all_agent_ids = sorted(["memory", "oracle", "worker"])
    assert out1["selected_agents"] == all_agent_ids


def test_single_agent_registry_deterministic() -> None:
    """Edge: single-agent registry is also deterministic."""
    registry = AgentRegistry()
    registry.register("solo", capabilities=["compute"])
    router = SwarmRouter(registry=registry)

    request = {"task": "compute hash", "context": {}}

    out1 = router.route(request)
    out2 = router.route(request)

    assert out1 == out2
    assert out1["selected_agents"] == ["solo"]


def test_registry_insertion_order_does_not_affect_routing() -> None:
    """
    Critical: registration order must NOT affect routing output.
    registry_A: memory -> oracle -> worker
    registry_B: worker -> oracle -> memory (reversed)
    Both must produce identical routing for same task.
    """
    request = {
        "task": "analyze ledger anomalies",
        "context": {"tenant_id": "order-test"},
    }

    registry_a = AgentRegistry()
    registry_a.register("memory", capabilities=["read", "write"])
    registry_a.register("oracle", capabilities=["audit", "analyze"])
    registry_a.register("worker", capabilities=["compute", "transform"])

    registry_b = AgentRegistry()
    registry_b.register("worker", capabilities=["compute", "transform"])
    registry_b.register("oracle", capabilities=["audit", "analyze"])
    registry_b.register("memory", capabilities=["read", "write"])

    out_a = SwarmRouter(registry=registry_a).route(request)
    out_b = SwarmRouter(registry=registry_b).route(request)

    # routing_hash must be identical (registry snapshot is sorted)
    assert out_a["routing_hash"] == out_b["routing_hash"]
    assert out_a["selected_agents"] == out_b["selected_agents"]
