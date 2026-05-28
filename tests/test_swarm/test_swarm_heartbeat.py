"""Tests for SwarmHeartbeat — includes thermodynamic ghost-eviction coverage."""

from __future__ import annotations

from cortex.extensions.swarm.swarm_heartbeat import NodeStatus, SwarmHeartbeat

# ── Basic lifecycle ────────────────────────────────────────────────────


def test_pulse_registers_and_marks_alive() -> None:
    hb = SwarmHeartbeat()
    hb.pulse("node-a", "Thread-A")
    vitals = hb.get_vitals()
    assert "node-a" in vitals
    assert vitals["node-a"].status == NodeStatus.ALIVE
    assert vitals["node-a"].pulse_count == 1


def test_reap_no_alerts_within_window() -> None:
    hb = SwarmHeartbeat()
    hb.pulse("node-b")
    alerts = hb.reap(timeout_seconds=60)
    assert alerts == []


def test_reap_transitions_to_suspect() -> None:
    hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=3)
    hb.pulse("node-c")
    # Force last_pulse into the past
    hb._registry["node-c"].last_pulse -= 999
    alerts = hb.reap(timeout_seconds=1)
    ids = [a.node_id for a in alerts]
    assert "node-c" in ids
    assert hb._registry["node-c"].status == NodeStatus.SUSPECT


def test_reap_transitions_to_dead() -> None:
    hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
    hb.pulse("node-d")
    hb._registry["node-d"].last_pulse -= 999
    hb.reap(timeout_seconds=1)  # miss 1 → SUSPECT
    hb._registry["node-d"].last_pulse -= 999
    hb.reap(timeout_seconds=1)  # miss 2 → DEAD
    assert hb._registry["node-d"].status == NodeStatus.DEAD


# ── Thermodynamic eviction ─────────────────────────────────────────────


def test_dead_node_evicted_after_recovery_window() -> None:
    """Ghost nodes must be auto-purged from the registry after dead_threshold + 2 misses."""
    hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
    hb.pulse("ghost-node")
    # Set last_pulse so far in the past that every reap considers it stale
    hb._registry["ghost-node"].last_pulse = 0.0

    # Run enough cycles: suspect(1) + dead(2) + eviction(4) = 4 reap cycles needed
    for _ in range(5):
        if "ghost-node" not in hb._registry:
            break
        hb.reap(timeout_seconds=1)

    assert "ghost-node" not in hb._registry, "Ghost node must be evicted from registry"


def test_alive_node_never_evicted() -> None:
    hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
    hb.pulse("live-node")
    # Reap multiple times — node keeps pulsing
    for _ in range(10):
        hb.pulse("live-node")
        hb.reap(timeout_seconds=60)
    assert "live-node" in hb._registry


def test_resurrection_after_eviction_re_registers() -> None:
    """After a ghost is evicted, a new pulse re-registers it cleanly."""
    hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
    hb.pulse("revive-node")
    hb._registry["revive-node"].last_pulse -= 9999
    for _ in range(5):
        hb._registry.get("revive-node") and hb.reap(timeout_seconds=1)
        if "revive-node" in hb._registry:
            hb._registry["revive-node"].last_pulse -= 9999

    # Node evicted — now re-register via pulse
    hb.pulse("revive-node")
    assert "revive-node" in hb._registry
    assert hb._registry["revive-node"].status == NodeStatus.ALIVE
    assert hb._registry["revive-node"].pulse_count == 1
