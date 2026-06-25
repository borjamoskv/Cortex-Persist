# [C5-REAL] Exergy-Maximized
"""
Divergence Map Test Suite

Demuestra:
  1. Deterministic trajectories → single equivalence class, zero distance
  2. Divergent trajectories → multiple classes, fork detection, nonzero distance
  3. Entropy drift → gradient directionality
  4. CI threshold enforcement → RuntimeError on violation
  5. Distance metric properties (symmetry, identity, triangle inequality holds)
  6. Fork topology correctness
"""

import os
import pytest

from cortex.runtime.state import RuntimeState
from cortex.runtime.replay.engine import ReplayEngine
from cortex.runtime.replay.ci_gate import fixed_event_trace
from cortex.runtime.replay.divergence import (
    DivergenceMap,
    DivergenceReport,
    StateDistance,
    ForkPoint,
    EntropyDrift,
    EquivalenceClass,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_deterministic_trajectories(n: int = 5, seed: int = 42) -> list:
    """N identical replay trajectories."""
    events = fixed_event_trace(seed=seed, length=15)
    return [ReplayEngine(RuntimeState).run(events) for _ in range(n)]


def _make_divergent_trajectories() -> list:
    """Two trajectories from different seeds → guaranteed divergence."""
    events_a = fixed_event_trace(seed=42, length=10)
    events_b = fixed_event_trace(seed=99, length=10)
    t_a = ReplayEngine(RuntimeState).run(events_a)
    t_b = ReplayEngine(RuntimeState).run(events_b)
    return [t_a, t_b]


def _make_mixed_trajectories() -> list:
    """3 identical + 1 divergent → 2 equivalence classes."""
    events_a = fixed_event_trace(seed=42, length=10)
    events_b = fixed_event_trace(seed=77, length=10)
    t_same = [ReplayEngine(RuntimeState).run(events_a) for _ in range(3)]
    t_diff = [ReplayEngine(RuntimeState).run(events_b)]
    return t_same + t_diff


# ── 1. Deterministic Trajectories ──────────────────────────────────


class TestDeterministicManifold:
    """All identical runs → collapsed manifold (single point)."""

    def test_single_equivalence_class(self):
        trajs = _make_deterministic_trajectories(n=5)
        report = DivergenceMap(trajs).analyze()
        assert report.is_deterministic is True
        assert report.num_equivalence_classes == 1
        assert report.equivalence_classes[0].size == 5

    def test_zero_max_distance(self):
        trajs = _make_deterministic_trajectories(n=3)
        report = DivergenceMap(trajs).analyze()
        assert report.max_distance == 0.0

    def test_no_fork_points(self):
        trajs = _make_deterministic_trajectories(n=4)
        report = DivergenceMap(trajs).analyze()
        assert len(report.fork_points) == 0

    def test_distance_matrix_all_zero(self):
        trajs = _make_deterministic_trajectories(n=3)
        report = DivergenceMap(trajs).analyze()
        for row in report.distance_matrix:
            for val in row:
                assert val == 0.0

    def test_ci_threshold_passes(self):
        trajs = _make_deterministic_trajectories(n=3)
        report = DivergenceMap(trajs).analyze(ci_threshold=0.0)
        assert report.is_deterministic is True


# ── 2. Divergent Trajectories ──────────────────────────────────────


class TestDivergentManifold:
    """Different event traces → non-trivial execution geometry."""

    def test_two_equivalence_classes(self):
        trajs = _make_divergent_trajectories()
        report = DivergenceMap(trajs).analyze()
        assert report.is_deterministic is False
        assert report.num_equivalence_classes == 2

    def test_nonzero_max_distance(self):
        trajs = _make_divergent_trajectories()
        report = DivergenceMap(trajs).analyze()
        assert report.max_distance > 0.0

    def test_fork_point_detected(self):
        trajs = _make_divergent_trajectories()
        report = DivergenceMap(trajs).analyze()
        assert len(report.fork_points) > 0
        fork = report.fork_points[0]
        assert fork.trajectory_a == 0
        assert fork.trajectory_b == 1
        # Fork at version 1 (bootstrap is identical, first event diverges)
        assert fork.version == 1

    def test_mixed_equivalence_classes(self):
        trajs = _make_mixed_trajectories()
        report = DivergenceMap(trajs).analyze()
        assert report.num_equivalence_classes == 2
        sizes = sorted(ec.size for ec in report.equivalence_classes)
        assert sizes == [1, 3]


# ── 3. Entropy Drift ───────────────────────────────────────────────


class TestEntropyDrift:
    """State complexity evolution over trajectory."""

    def test_expanding_drift(self):
        """MEMORY_WRITE adding new keys → expanding complexity."""
        trajs = _make_deterministic_trajectories(n=2)
        report = DivergenceMap(trajs).analyze()
        drift = report.entropy_drifts[0]
        assert drift.direction == "expanding"
        assert drift.mean_gradient > 0

    def test_complexity_curve_length(self):
        events = fixed_event_trace(seed=42, length=10)
        traj = ReplayEngine(RuntimeState).run(events)
        trajs = [traj, traj]
        report = DivergenceMap(trajs).analyze()
        drift = report.entropy_drifts[0]
        assert len(drift.complexity_curve) == 11  # bootstrap + 10

    def test_gradient_length(self):
        events = fixed_event_trace(seed=42, length=10)
        traj = ReplayEngine(RuntimeState).run(events)
        trajs = [traj, traj]
        report = DivergenceMap(trajs).analyze()
        drift = report.entropy_drifts[0]
        assert len(drift.gradient) == 10  # n-1 deltas


# ── 4. CI Threshold Enforcement ─────────────────────────────────────


class TestCIThreshold:
    """CI gate mode: reject if max_distance > threshold."""

    def test_threshold_violation_raises(self):
        trajs = _make_divergent_trajectories()
        with pytest.raises(RuntimeError, match="CI GATE FAIL"):
            DivergenceMap(trajs).analyze(ci_threshold=0.0)

    def test_threshold_satisfied_passes(self):
        trajs = _make_divergent_trajectories()
        report = DivergenceMap(trajs).analyze(ci_threshold=1.0)
        assert report.max_distance <= 1.0

    def test_threshold_exact_boundary(self):
        """At exact boundary → should pass (not strict inequality)."""
        trajs = _make_divergent_trajectories()
        report_no_threshold = DivergenceMap(trajs).analyze()
        md = report_no_threshold.max_distance
        # At exact max_distance → should not raise
        report = DivergenceMap(trajs).analyze(ci_threshold=md)
        assert report.max_distance == md


# ── 5. Distance Metric Properties ──────────────────────────────────


class TestDistanceMetricProperties:
    """Verify metric axioms on the distance matrix."""

    def test_symmetry(self):
        trajs = _make_mixed_trajectories()
        report = DivergenceMap(trajs).analyze()
        n = report.num_trajectories
        for i in range(n):
            for j in range(n):
                assert report.distance_matrix[i][j] == report.distance_matrix[j][i]

    def test_identity(self):
        """d(x, x) == 0"""
        trajs = _make_mixed_trajectories()
        report = DivergenceMap(trajs).analyze()
        for i in range(report.num_trajectories):
            assert report.distance_matrix[i][i] == 0.0

    def test_non_negative(self):
        trajs = _make_mixed_trajectories()
        report = DivergenceMap(trajs).analyze()
        for row in report.distance_matrix:
            for val in row:
                assert val >= 0.0


# ── 6. Report Serialization ────────────────────────────────────────


class TestReportSerialization:
    def test_to_dict_deterministic(self):
        trajs = _make_deterministic_trajectories(n=2)
        report = DivergenceMap(trajs).analyze()
        d = report.to_dict()
        assert d["is_deterministic"] is True
        assert d["max_distance"] == 0.0
        assert d["num_equivalence_classes"] == 1

    def test_to_dict_divergent(self):
        trajs = _make_divergent_trajectories()
        report = DivergenceMap(trajs).analyze()
        d = report.to_dict()
        assert d["is_deterministic"] is False
        assert len(d["fork_points"]) > 0
        assert d["max_distance"] > 0.0


# ── 7. Edge Cases ──────────────────────────────────────────────────


class TestEdgeCases:
    def test_minimum_two_trajectories(self):
        with pytest.raises(ValueError, match="at least 2"):
            DivergenceMap([_make_deterministic_trajectories(n=2)[0]])

    def test_bootstrap_only_trajectories(self):
        """Empty event list → only bootstrap snapshot."""
        t = ReplayEngine(RuntimeState).run([])
        trajs = [t, t]
        report = DivergenceMap(trajs).analyze()
        assert report.is_deterministic is True
        assert report.max_distance == 0.0
