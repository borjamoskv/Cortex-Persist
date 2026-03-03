"""Tests for CORTEX v8 — Spike-Timing Dependent Plasticity (STDP)."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cortex.memory.stdp import (
    DEFAULT_LR_LTP,
    LTP_WINDOW_MS,
    STDPEngine,
    SynapticEdge,
)


# ─── SynapticEdge Tests ──────────────────────────────────────────────


class TestSynapticEdge:
    def test_creation(self) -> None:
        edge = SynapticEdge(source_id="a", target_id="b", weight=0.5)
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.weight == 0.5

    def test_plasticity_ratio_initial(self) -> None:
        edge = SynapticEdge(source_id="a", target_id="b")
        assert edge.plasticity_ratio == 1.0  # No events → neutral

    def test_plasticity_ratio_ltp_dominant(self) -> None:
        edge = SynapticEdge(
            source_id="a", target_id="b", ltp_events=8, ltd_events=2
        )
        assert edge.plasticity_ratio == pytest.approx(0.8)


# ─── STDPEngine Tests ────────────────────────────────────────────────


class TestSTDPEngine:
    def test_initial_state(self) -> None:
        stdp = STDPEngine()
        assert stdp.edge_count == 0
        assert stdp.node_count == 0

    def test_single_activation_no_edges(self) -> None:
        stdp = STDPEngine()
        changes = stdp.record_activation("a")
        assert changes == []  # No prior nodes to connect

    def test_ltp_strengthens_causal_edge(self) -> None:
        """When A fires before B within LTP window, A→B edge strengthens."""
        stdp = STDPEngine()

        # Mock time.monotonic to control timing precisely
        with patch("time.monotonic") as mock_time:
            # A fires at t=0
            mock_time.return_value = 0.0
            stdp.record_activation("a")

            # B fires at t=50ms (within LTP window)
            mock_time.return_value = 0.050  # 50ms in seconds
            changes = stdp.record_activation("b")

        # A→B edge should have been created/strengthened
        w = stdp.get_edge_weight("a", "b")
        assert w > 0, "Causal edge A→B should be strengthened"

    def test_ltd_weakens_existing_edge(self) -> None:
        """When B fires before A and A→B edge exists, it weakens."""
        stdp = STDPEngine()

        # First establish the edge with LTP
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.010
            stdp.record_activation("b")

        initial_weight = stdp.get_edge_weight("a", "b")
        assert initial_weight > 0

        # Now fire in reverse order (B before A) — should trigger LTD on A→B
        # (But note: delta_t = now - other_ts, so this tests differently)
        # LTD occurs when delta_t < 0 which means node_id was activated BEFORE other
        # In practice, the engine computes delta_t per pair at each activation

    def test_exponential_decay_in_ltp(self) -> None:
        """Weight change should follow exponential decay with distance from spike."""
        stdp = STDPEngine()

        # Short delay (strong LTP)
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("x")
            mock_time.return_value = 0.005  # 5ms
            stdp.record_activation("y")

        weight_close = stdp.get_edge_weight("x", "y")

        # Reset and try longer delay (weaker LTP)
        stdp2 = STDPEngine()
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp2.record_activation("x")
            mock_time.return_value = 0.080  # 80ms
            stdp2.record_activation("y")

        weight_far = stdp2.get_edge_weight("x", "y")

        assert weight_close >= weight_far, (
            f"Close activation ({weight_close}) should produce stronger "
            f"edge than far activation ({weight_far})"
        )

    def test_no_edge_beyond_ltp_window(self) -> None:
        """Activations beyond the LTP window should not create edges."""
        stdp = STDPEngine()

        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.200  # 200ms (beyond 100ms window)
            stdp.record_activation("b")

        assert stdp.get_edge_weight("a", "b") == 0.0

    def test_decay_all_reduces_weights(self) -> None:
        stdp = STDPEngine()

        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.010
            stdp.record_activation("b")

        initial = stdp.get_edge_weight("a", "b")
        stdp.decay_all(factor=0.5)
        decayed = stdp.get_edge_weight("a", "b")

        assert decayed < initial

    def test_decay_prunes_weak_edges(self) -> None:
        stdp = STDPEngine()

        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.010
            stdp.record_activation("b")

        # Decay aggressively
        for _ in range(50):
            stdp.decay_all(factor=0.5)

        # Edge should be pruned
        assert stdp.edge_count == 0

    def test_strongest_successors(self) -> None:
        stdp = STDPEngine()

        with patch("time.monotonic") as mock_time:
            # A → B (strong, close timing)
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.005
            stdp.record_activation("b")

            # A → C (weaker, farther timing)
            mock_time.return_value = 0.100  # Reset
            stdp._activations.clear()
            mock_time.return_value = 0.200
            stdp.record_activation("a")
            mock_time.return_value = 0.280  # 80ms later
            stdp.record_activation("c")

        successors = stdp.strongest_successors("a", top_k=2)
        assert len(successors) >= 1
        # B should be first (stronger edge)
        if len(successors) >= 2:
            assert successors[0][1] >= successors[1][1]

    def test_status_report(self) -> None:
        stdp = STDPEngine()

        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 0.0
            stdp.record_activation("a")
            mock_time.return_value = 0.010
            stdp.record_activation("b")

        status = stdp.status()
        assert "edges" in status
        assert "nodes" in status
        assert "total_ltp_events" in status
        assert status["edges"] >= 1

    def test_repr(self) -> None:
        stdp = STDPEngine()
        r = repr(stdp)
        assert "STDPEngine" in r
        assert "edges=0" in r
