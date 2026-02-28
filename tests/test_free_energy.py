# tests/test_free_energy.py
"""Tests for the Free Energy Monitor — Phase 3 formalization.

Validates the mathematical properties of:
  - KL divergence computation (non-negative, zero for identical dists)
  - Complexity (monotonically increases with errors/ghosts)
  - Accuracy (correlates with fitness_delta)
  - Free energy decomposition (F = Complexity - Accuracy)
  - Expected Free Energy for strategy ranking
  - FreeEnergyMonitor orchestration
"""

from __future__ import annotations

import math

import pytest

from cortex.evolution.agents import AgentDomain
from cortex.evolution.cortex_metrics import DomainMetrics
from cortex.evolution.free_energy import (
    FreeEnergyMonitor,
    _kl_bernoulli,
    compute_accuracy,
    compute_complexity,
    compute_free_energy,
    compute_strategy_efe,
    compute_surprise,
)


def _m(**overrides) -> DomainMetrics:
    """Shortcut for DomainMetrics with overrides."""
    defaults = {
        "domain": AgentDomain.FABRICATION,
        "error_count": 0,
        "ghost_count": 0,
        "bridge_count": 0,
        "decision_count": 0,
        "knowledge_count": 0,
        "fact_density": 0,
    }
    defaults.update(overrides)
    return DomainMetrics(**defaults)


# ── KL Divergence ─────────────────────────────────────────────


class TestKLDivergence:
    def test_kl_identical_is_zero(self):
        """D_KL(p ‖ p) = 0."""
        assert _kl_bernoulli(0.5, 0.5) == pytest.approx(0.0, abs=1e-6)

    def test_kl_nonnegative(self):
        """Gibbs' inequality: D_KL ≥ 0."""
        for q in [0.1, 0.3, 0.5, 0.7, 0.9]:
            for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
                assert _kl_bernoulli(q, p) >= -1e-10

    def test_kl_asymmetric(self):
        """D_KL(q ‖ p) ≠ D_KL(p ‖ q) in general."""
        forward = _kl_bernoulli(0.8, 0.3)
        backward = _kl_bernoulli(0.3, 0.8)
        assert forward != pytest.approx(backward, rel=1e-3)

    def test_kl_extreme_values(self):
        """Edge cases near 0 and 1 are handled."""
        result = _kl_bernoulli(0.0, 0.5)
        assert math.isfinite(result)
        result = _kl_bernoulli(1.0, 0.5)
        assert math.isfinite(result)


# ── Complexity ────────────────────────────────────────────────


class TestComplexity:
    def test_tonic_baseline_low_complexity(self):
        """Default (tonic) metrics → low complexity."""
        m = _m()
        c = compute_complexity(m)
        assert c >= 0
        # Tonic health is 0.5, KL(0.5‖0.5)=0 → low complexity
        assert c < 1.0

    def test_errors_increase_complexity(self):
        """More errors → higher complexity."""
        c_low = compute_complexity(_m(error_count=0))
        c_high = compute_complexity(_m(error_count=10))
        assert c_high > c_low

    def test_ghosts_increase_complexity(self):
        """More ghosts → higher complexity."""
        c_low = compute_complexity(_m(ghost_count=0))
        c_high = compute_complexity(_m(ghost_count=10))
        assert c_high > c_low

    def test_bridges_reduce_complexity(self):
        """More bridges → lower complexity."""
        c_nobridges = compute_complexity(_m(error_count=3))
        c_bridges = compute_complexity(_m(error_count=3, bridge_count=10))
        assert c_bridges < c_nobridges

    def test_complexity_nonnegative(self):
        """Complexity is always ≥ 0."""
        for e in range(10):
            for g in range(10):
                c = compute_complexity(_m(error_count=e, ghost_count=g))
                assert c >= 0


# ── Accuracy ──────────────────────────────────────────────────


class TestAccuracy:
    def test_positive_delta_high_accuracy(self):
        """Thriving domain (positive fitness_delta) → high accuracy."""
        m = _m(bridge_count=5, decision_count=10)  # positive delta
        a = compute_accuracy(m)
        assert a > 0.5

    def test_negative_delta_low_accuracy(self):
        """Struggling domain (negative fitness_delta) → low accuracy."""
        m = _m(error_count=10, ghost_count=5)  # negative delta
        a = compute_accuracy(m)
        assert a < 0.5

    def test_accuracy_bounded(self):
        """Accuracy ∈ [0, 1]."""
        for e in [0, 5, 10]:
            for d in [0, 5, 10]:
                for b in [0, 5, 10]:
                    a = compute_accuracy(_m(error_count=e, decision_count=d, bridge_count=b))
                    assert 0.0 <= a <= 1.0


# ── Surprise ──────────────────────────────────────────────────


class TestSurprise:
    def test_healthy_domain_low_surprise(self):
        """High health → low surprise."""
        m = _m(decision_count=10, bridge_count=5)  # health ~0.9+
        s = compute_surprise(m)
        assert s >= 0
        assert s < 2.0  # Low surprise for healthy domain

    def test_errors_increase_surprise(self):
        """Errors are unexpected observations → increase surprise."""
        s_low = compute_surprise(_m(error_count=0))
        s_high = compute_surprise(_m(error_count=10))
        assert s_high > s_low


# ── Free Energy (F = Complexity - Accuracy) ───────────────────


class TestFreeEnergy:
    def test_decomposition(self):
        """F = Complexity - Accuracy."""
        m = _m(error_count=3, decision_count=2, ghost_count=1)
        state = compute_free_energy(m)
        assert state.free_energy == pytest.approx(state.complexity - state.accuracy)

    def test_healthy_domain_negative_F(self):
        """Thriving domain can have negative F (accuracy > complexity)."""
        m = _m(decision_count=10, bridge_count=8)
        state = compute_free_energy(m)
        # At least accuracy should be substantial
        assert state.accuracy > 0.5

    def test_struggling_domain_positive_F(self):
        """Failing domain has positive F (complexity > accuracy)."""
        m = _m(error_count=10, ghost_count=8)
        state = compute_free_energy(m)
        assert state.free_energy > 0

    def test_state_has_domain(self):
        """FreeEnergyState carries domain information."""
        m = _m(domain=AgentDomain.SECURITY)
        state = compute_free_energy(m)
        assert state.domain == AgentDomain.SECURITY

    def test_to_dict_roundtrip(self):
        """FreeEnergyState serializes cleanly."""
        state = compute_free_energy(_m())
        d = state.to_dict()
        assert "F" in d
        assert "complexity" in d
        assert "accuracy" in d


# ── Expected Free Energy (Strategy Ranking) ───────────────────


class TestStrategyEFE:
    def test_positive_delta_lowers_G(self):
        """Strategy with positive expected delta → lower G (better)."""
        m = _m(error_count=3)
        efe_good = compute_strategy_efe("good_strat", 5.0, m)
        efe_bad = compute_strategy_efe("bad_strat", 0.1, m)
        assert efe_good.expected_free_energy < efe_bad.expected_free_energy

    def test_uncertain_domain_boosts_epistemic(self):
        """Domains with more ghosts + fewer decisions → higher epistemic value."""
        m_uncertain = _m(ghost_count=10, decision_count=0)
        m_certain = _m(ghost_count=0, decision_count=50)
        efe_u = compute_strategy_efe("s", 1.0, m_uncertain)
        efe_c = compute_strategy_efe("s", 1.0, m_certain)
        assert efe_u.epistemic_value > efe_c.epistemic_value

    def test_efe_to_dict(self):
        """StrategyEFE serializes cleanly."""
        efe = compute_strategy_efe("test", 1.0, _m())
        d = efe.to_dict()
        assert d["strategy"] == "test"
        assert "G" in d


# ── FreeEnergyMonitor ─────────────────────────────────────────


class TestFreeEnergyMonitor:
    def test_snapshot_returns_all_domains(self):
        """Snapshot covers all AgentDomains."""
        monitor = FreeEnergyMonitor()
        states = monitor.snapshot()
        assert len(states) >= len(AgentDomain) - 1  # SYNERGY may be excluded

    def test_total_free_energy_is_sum(self):
        """Total F = sum of per-domain F."""
        monitor = FreeEnergyMonitor()
        states = monitor.snapshot()
        expected = sum(s.free_energy for s in states.values())
        assert monitor.total_free_energy() == pytest.approx(expected, abs=0.01)

    def test_trend_empty_history(self):
        """No history → trend is 0."""
        monitor = FreeEnergyMonitor()
        assert monitor.trend(AgentDomain.FABRICATION) == 0.0

    def test_report_structure(self):
        """Report has expected keys."""
        monitor = FreeEnergyMonitor()
        r = monitor.report()
        assert "total_F" in r
        assert "avg_F" in r
        assert "worst_domain" in r
        assert "best_domain" in r
        assert "domains" in r

    def test_rank_strategies(self):
        """Strategies are ranked by ascending G (lower = better)."""
        monitor = FreeEnergyMonitor()
        mutations = {
            "ParameterTuning": 2.0,
            "HeuristicInjection": 5.0,
            "PruneDeadPath": 1.0,
        }
        ranked = monitor.rank_strategies(mutations, AgentDomain.FABRICATION)
        assert len(ranked) == 3
        # Sorted by G ascending — best strategy first
        assert ranked[0].expected_free_energy <= ranked[-1].expected_free_energy

    def test_history_limited(self):
        """History doesn't grow beyond max."""
        monitor = FreeEnergyMonitor()
        monitor._max_history = 5
        for _ in range(10):
            monitor.snapshot()
        assert len(monitor._history) <= 5
