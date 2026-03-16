"""Tests for strategies.py — S0 through S3 resolution."""

from __future__ import annotations

from benchmarks.encb.agents import AdversaryType, NodeProfile
from benchmarks.encb.belief_object import BeliefType
from benchmarks.encb.strategies import (
    PropState,
    resolve_cortex,
    resolve_crdt_only,
    resolve_lww,
    resolve_rag,
)


def _honest_node(nid: str = "n0", rel: float = 0.8) -> NodeProfile:
    return NodeProfile(
        node_id=nid, adversary_type=AdversaryType.HONEST, reliability=rel,
    )


def _liar_node(nid: str = "liar", rel: float = 0.1) -> NodeProfile:
    return NodeProfile(
        node_id=nid, adversary_type=AdversaryType.RANDOM_LIAR, reliability=rel,
    )


class TestPropState:
    """Test PropState correctness checks."""

    def test_boolean_correct(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        s.current_value = True
        assert s.is_correct()

    def test_boolean_incorrect(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        s.current_value = False
        assert not s.is_correct()

    def test_scalar_within_tolerance(self):
        s = PropState("k", BeliefType.SCALAR, 100.0)
        s.current_value = 105.0  # 5% off
        assert s.is_correct()

    def test_scalar_outside_tolerance(self):
        s = PropState("k", BeliefType.SCALAR, 100.0)
        s.current_value = 120.0  # 20% off
        assert not s.is_correct()

    def test_set_exact_match(self):
        s = PropState("k", BeliefType.SET, {"a", "b"})
        s.current_value = {"b", "a"}
        assert s.is_correct()

    def test_set_mismatch(self):
        s = PropState("k", BeliefType.SET, {"a", "b"})
        s.current_value = {"a", "c"}
        assert not s.is_correct()

    def test_none_value(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        assert not s.is_correct()


class TestLWW:
    """Test S0 — Last-Write-Wins."""

    def test_last_observation_wins(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (_honest_node("n0"), True, 0.9),
            (_liar_node("n1"), False, 0.5),
        ]
        resolve_lww(s, obs, 0)
        assert s.current_value is False  # last wins, not best

    def test_empty_observations(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        resolve_lww(s, [], 0)
        assert s.current_value is None


class TestRAG:
    """Test S1 — RAG Summary Overwrite."""

    def test_majority_wins_boolean(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (_honest_node("n0"), True, 0.9),
            (_honest_node("n1"), True, 0.8),
            (_liar_node("n2"), False, 0.5),
        ]
        resolve_rag(s, obs, 0)
        assert s.current_value is True

    def test_categorical_highest_tally(self):
        s = PropState("k", BeliefType.CATEGORICAL, "python",
                       categories=["python", "go", "rust"])
        obs = [
            (_honest_node("n0"), "python", 0.9),
            (_honest_node("n1"), "python", 0.8),
            (_liar_node("n2"), "go", 0.5),
        ]
        resolve_rag(s, obs, 0)
        assert s.current_value == "python"

    def test_scalar_median(self):
        s = PropState("k", BeliefType.SCALAR, 100.0)
        obs = [
            (_honest_node("n0"), 99.0, 0.9),
            (_honest_node("n1"), 101.0, 0.9),
            (_liar_node("n2"), 500.0, 0.5),
        ]
        resolve_rag(s, obs, 0)
        assert s.current_value == 101.0  # median


class TestCRDTOnly:
    """Test S2 — CRDT-only."""

    def test_boolean_convergence(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (_honest_node("n0"), True, 0.9),
            (_honest_node("n1"), True, 0.8),
            (_liar_node("n2"), False, 0.3),
        ]
        resolve_crdt_only(s, obs, 0)
        assert s.current_value is True  # majority confidence


class TestCortex:
    """Test S3 — Full Cortex."""

    def test_honest_majority_resolves_correctly(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (_honest_node("n0", 0.9), True, 0.85),
            (_honest_node("n1", 0.85), True, 0.8),
            (_liar_node("n2", 0.1), False, 0.95),
        ]
        resolve_cortex(s, obs, 0)
        assert s.current_value is True

    def test_reliability_update_happens(self):
        n1 = _honest_node("n0", 0.5)
        n2 = _liar_node("n1", 0.5)
        n3 = _honest_node("n2", 0.5)
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (n1, True, 0.9),
            (n3, True, 0.85),
            (n2, False, 0.7),
        ]
        # Run at round 5 (past warm-up) so full LogOP applies
        resolve_cortex(s, obs, 5)
        # After resolution, honest node reliability should increase
        # and liar node reliability should decrease
        assert n1.reliability > 0.5  # was correct
        assert n2.reliability < 0.5  # was wrong

    def test_no_reliability_mode(self):
        s = PropState("k", BeliefType.BOOLEAN, True)
        obs = [
            (_honest_node("n0", 0.9), True, 0.85),
            (_liar_node("n1", 0.1), False, 0.95),
        ]
        resolve_cortex(s, obs, 0, use_reliability=False)
        # Should still resolve, but without reliability weighting
        assert s.current_value is not None

    def test_categorical(self):
        s = PropState("k", BeliefType.CATEGORICAL, "python",
                       categories=["python", "go", "rust"])
        obs = [
            (_honest_node("n0", 0.9), "python", 0.9),
            (_honest_node("n1", 0.85), "python", 0.8),
            (_liar_node("n2", 0.1), "go", 0.95),
        ]
        resolve_cortex(s, obs, 0)
        assert s.current_value == "python"
