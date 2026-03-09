"""Tests for SwarmHeartbeat — Ω₃ Byzantine Default (Distributed Liveness)."""

from __future__ import annotations

import time

import pytest

from cortex.swarm.swarm_heartbeat import (
    SWARM_HEARTBEAT,
    NodeStatus,
    SwarmHeartbeat,
)
from cortex.daemon.monitors.swarm_heartbeat import (
    SwarmHeartbeatMonitor,
)


@pytest.fixture(autouse=True)
def fresh_heartbeat():
    """Reset the global heartbeat registry before each test."""
    SWARM_HEARTBEAT.reset()
    yield
    SWARM_HEARTBEAT.reset()


class TestPulse:
    """Test node registration and pulse recording."""

    def test_pulse_registers_node(self):
        SWARM_HEARTBEAT.pulse("node_a", "ThreadA")
        vitals = SWARM_HEARTBEAT.get_vitals()
        assert "node_a" in vitals
        assert vitals["node_a"].thread_name == "ThreadA"
        assert vitals["node_a"].status == NodeStatus.ALIVE

    def test_pulse_increments_count(self):
        SWARM_HEARTBEAT.pulse("node_b", "ThreadB")
        SWARM_HEARTBEAT.pulse("node_b", "ThreadB")
        SWARM_HEARTBEAT.pulse("node_b", "ThreadB")
        vitals = SWARM_HEARTBEAT.get_vitals()
        assert vitals["node_b"].pulse_count == 3

    def test_pulse_resets_miss_count(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
        hb.pulse("n", "T")
        # Manually set miss_count to simulate a reap cycle
        hb._registry["n"].miss_count = 5
        hb._registry["n"].status = NodeStatus.SUSPECT
        hb.pulse("n", "T")
        assert hb._registry["n"].miss_count == 0
        assert hb._registry["n"].status == NodeStatus.ALIVE


class TestReap:
    """Test the reaper's SUSPECT/DEAD state transitions."""

    def test_reap_no_alerts_when_all_alive(self):
        SWARM_HEARTBEAT.pulse("alive_node", "T")
        alerts = SWARM_HEARTBEAT.reap(timeout_seconds=120.0)
        assert alerts == []

    def test_reap_transitions_to_suspect(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=3)
        hb.pulse("slow_node", "SlowThread")
        # Manually backdate the pulse
        hb._registry["slow_node"].last_pulse = time.monotonic() - 200
        alerts = hb.reap(timeout_seconds=60.0)
        assert len(alerts) == 1
        assert alerts[0].status == NodeStatus.SUSPECT

    def test_reap_transitions_to_dead(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
        hb.pulse("dying_node", "DyingThread")
        hb._registry["dying_node"].last_pulse = time.monotonic() - 300

        # First reap → SUSPECT
        hb.reap(timeout_seconds=60.0)
        assert hb._registry["dying_node"].status == NodeStatus.SUSPECT

        # Second reap → DEAD
        alerts = hb.reap(timeout_seconds=60.0)
        assert len(alerts) == 1
        assert alerts[0].status == NodeStatus.DEAD

    def test_reap_does_not_realert_dead(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
        hb.pulse("dead_node", "T")
        hb._registry["dead_node"].last_pulse = time.monotonic() - 500

        hb.reap(timeout_seconds=60.0)  # → SUSPECT
        hb.reap(timeout_seconds=60.0)  # → DEAD
        alerts = hb.reap(timeout_seconds=60.0)  # Already DEAD
        assert alerts == []  # No new alerts


class TestResurrection:
    """Test that dead nodes can return to ALIVE via pulse."""

    def test_pulse_resurrects_dead_node(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
        hb.pulse("zombie", "ZombieThread")
        hb._registry["zombie"].last_pulse = time.monotonic() - 500
        hb.reap(timeout_seconds=10.0)  # SUSPECT
        hb.reap(timeout_seconds=10.0)  # DEAD
        assert hb._registry["zombie"].status == NodeStatus.DEAD

        hb.pulse("zombie", "ZombieThread")
        assert hb._registry["zombie"].status == NodeStatus.ALIVE
        assert hb._registry["zombie"].miss_count == 0


class TestStatusSummary:
    """Test the one-line summary."""

    def test_all_alive_summary(self):
        SWARM_HEARTBEAT.pulse("a", "A")
        SWARM_HEARTBEAT.pulse("b", "B")
        summary = SWARM_HEARTBEAT.status_summary()
        assert "2/2 ALIVE" in summary
        assert "0 SUSPECT" in summary
        assert "0 DEAD" in summary

    def test_empty_summary(self):
        summary = SWARM_HEARTBEAT.status_summary()
        assert "0/0 ALIVE" in summary


class TestUnregister:
    """Test graceful node removal."""

    def test_unregister_removes_node(self):
        SWARM_HEARTBEAT.pulse("temp", "TempThread")
        assert SWARM_HEARTBEAT.unregister("temp") is True
        assert "temp" not in SWARM_HEARTBEAT.get_vitals()

    def test_unregister_missing_returns_false(self):
        assert SWARM_HEARTBEAT.unregister("nonexistent") is False


class TestSwarmHeartbeatMonitor:
    """Test the daemon monitor integration."""

    def test_check_returns_alerts_for_dead_nodes(self):
        hb = SwarmHeartbeat(suspect_threshold=1, dead_threshold=2)
        hb.pulse("monitored", "MonThread")
        hb._registry["monitored"].last_pulse = time.monotonic() - 300

        hb.reap(timeout_seconds=60.0)  # SUSPECT
        hb.reap(timeout_seconds=60.0)  # DEAD

        # Use the global singleton for the monitor
        SWARM_HEARTBEAT.pulse("test_node", "TestThread")
        SWARM_HEARTBEAT._registry["test_node"].last_pulse = (
            time.monotonic() - 500
        )

        monitor = SwarmHeartbeatMonitor(timeout_seconds=60.0)
        # First check increments miss_count to 1 (status is still ALIVE)
        alerts1 = monitor.check()
        assert len(alerts1) == 0

        # Second check increments miss_count to 2 (status transitions to SUSPECT)
        alerts2 = monitor.check()
        assert len(alerts2) == 1
        assert alerts2[0].status == "SUSPECT"

    def test_check_returns_empty_when_all_healthy(self):
        SWARM_HEARTBEAT.pulse("healthy", "HealthyThread")
        monitor = SwarmHeartbeatMonitor(timeout_seconds=120.0)
        alerts = monitor.check()
        assert alerts == []
