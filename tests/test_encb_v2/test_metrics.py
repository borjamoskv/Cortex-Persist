"""Tests for metrics.py — PFBR, TER, EDI, CNCL."""

from __future__ import annotations

from benchmarks.encb.agents import AdversaryType, NodeProfile
from benchmarks.encb.belief_object import BeliefType
from benchmarks.encb.metrics import cncl, cncl_avg, edi, pfbr, ter
from benchmarks.encb.strategies import PropState


def _state(correct: bool, conf: float = 0.5) -> PropState:
    s = PropState("k", BeliefType.BOOLEAN, True)
    s.current_value = True if correct else False
    s.confidence = conf
    s.conflict_mass = 0.0 if correct else 0.5
    return s


class TestPFBR:
    """Test Persistent False Belief Rate."""

    def test_all_correct(self):
        states = [_state(True) for _ in range(10)]
        assert pfbr(states) == 0.0

    def test_all_wrong(self):
        states = [_state(False) for _ in range(10)]
        assert pfbr(states) == 1.0

    def test_half_wrong(self):
        states = [_state(True)] * 5 + [_state(False)] * 5
        assert abs(pfbr(states) - 0.5) < 1e-6

    def test_empty(self):
        assert pfbr([]) == 0.0


class TestTER:
    """Test Time to Epistemic Recovery."""

    def test_immediate_recovery(self):
        snapshots = [[_state(True)] * 10]
        result = ter(snapshots, alpha=0.9, beta=0.9, gamma=0.1)
        assert result == 0

    def test_never_recovers(self):
        snapshots = [[_state(False)] * 10 for _ in range(30)]
        result = ter(snapshots)
        assert result is None

    def test_recovery_at_round_5(self):
        snapshots = []
        for t in range(10):
            if t < 5:
                snapshots.append([_state(False)] * 10)
            else:
                snapshots.append([_state(True)] * 10)
        result = ter(snapshots)
        assert result == 5


class TestEDI:
    """Test Epistemic Debt Integral."""

    def test_zero_debt(self):
        snapshots = [[_state(True)] * 10 for _ in range(5)]
        assert edi(snapshots) == 0.0

    def test_accumulates(self):
        snapshots = [[_state(False)] * 10 for _ in range(5)]
        result = edi(snapshots)
        assert result > 0

    def test_more_rounds_more_debt(self):
        snap5 = [[_state(False)] * 10 for _ in range(5)]
        snap10 = [[_state(False)] * 10 for _ in range(10)]
        assert edi(snap10) > edi(snap5)


class TestCNCL:
    """Test Corrupt Node Containment Latency."""

    def test_contained(self):
        nodes = [
            NodeProfile(
                node_id="liar",
                adversary_type=AdversaryType.RANDOM_LIAR,
            ),
        ]
        history = {"liar": [0.5, 0.4, 0.3, 0.15, 0.10]}
        result = cncl(history, nodes, threshold=0.20)
        assert result["liar"] == 3  # first round below threshold

    def test_never_contained(self):
        nodes = [
            NodeProfile(
                node_id="liar",
                adversary_type=AdversaryType.RANDOM_LIAR,
            ),
        ]
        history = {"liar": [0.5, 0.45, 0.40, 0.35, 0.30]}
        result = cncl(history, nodes, threshold=0.20)
        assert result["liar"] is None

    def test_honest_excluded(self):
        nodes = [
            NodeProfile(
                node_id="honest",
                adversary_type=AdversaryType.HONEST,
            ),
        ]
        history = {"honest": [0.9, 0.85, 0.80]}
        result = cncl(history, nodes, threshold=0.20)
        assert "honest" not in result

    def test_cncl_avg_computed(self):
        containments = {"l1": 3, "l2": 5, "l3": None}
        avg = cncl_avg(containments)
        assert avg == 4.0

    def test_cncl_avg_none(self):
        containments = {"l1": None, "l2": None}
        assert cncl_avg(containments) is None
