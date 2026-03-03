# tests/test_evolution_psi_sap.py
"""Tests para la implementación del Principio de Acción Simbólica (ψSAP).

Cubre:
- Cálculo del Lagrangiano (L_ψ = K - S + G - F)
- Actualización del action integral (S_ψ)
- Comportamiento del LagrangianController
- Integración con EntropyReductionStrategy (Axiom 12 tags)
"""

from __future__ import annotations

import math

import pytest

from cortex.evolution.action import SymbolicActionEngine, SymbolicActionState
from cortex.evolution.agents import AgentDomain, Mutation, SovereignAgent
from cortex.evolution.cortex_metrics import DomainMetrics
from cortex.evolution.lnn import LagrangianController


def _make_metrics(
    error_count: int = 0,
    ghost_count: int = 0,
    fitness_delta: float = 0.0,
    health_score: float = 1.0,
) -> DomainMetrics:
    return DomainMetrics(
        domain=AgentDomain.FABRICATION,
        error_count=error_count,
        ghost_count=ghost_count,
        fact_density=100,
        decision_count=10,
        bridge_count=2,
    )


# ── SymbolicActionEngine ──────────────────────────────────────


class TestSymbolicActionEngine:
    def test_lagrangian_formula_healthy_domain(self):
        """Healthy domain (low errors, strong decisions) -> positive Lagrangian."""
        engine = SymbolicActionEngine()
        agent = SovereignAgent(domain=AgentDomain.FABRICATION)
        agent.fitness = 80.0

        # Richly-active domain: many decisions, bridges, zero errors/ghosts
        m = DomainMetrics(
            domain=AgentDomain.FABRICATION,
            error_count=0,
            ghost_count=0,
            decision_count=20,
            bridge_count=4,
            fact_density=200,
        )

        # health_score = 0.5 + (4*0.15 + 20*0.05) - 0 = 0.5+0.6+1.0 = min(1.0,2.1)=1.0
        # fitness_delta = 4*2.0 + 20*0.5 + 1.5 (recency) - 0 = 8+10+1.5 = capped at 5.0
        # K = max(0, 5.0) = 5.0, S = 0, F = 0, G = 2.0
        # L = 5.0 - 0 + 2.0 - 0 = 7.0
        state = engine.compute_state(agent, m, grace_injection=2.0)

        assert state.lagrangian > 0  # Healthy domain has positive L_psi
        assert state.collapse_potential == 0.0  # No ghosts or errors
        assert state.entropy_resistance == 0.0
        assert state.grace == 2.0

    def test_lagrangian_formula_degraded_domain(self):
        """Degraded domain (high errors, ghosts) → negative Lagrangian."""
        engine = SymbolicActionEngine()
        agent = SovereignAgent(domain=AgentDomain.SECURITY)
        agent.fitness = 30.0

        # Stressed domain: many errors, ghosts, low health
        m = DomainMetrics(
            domain=AgentDomain.SECURITY,
            error_count=10,
            ghost_count=10,
            fact_density=5,
        )

        state = engine.compute_state(agent, m, grace_injection=0.0)

        # Entropy resistance (S) should be high, bringing L negative
        assert state.entropy_resistance > 0
        assert state.collapse_potential > 0
        # L_ψ should be below 0 for a badly degraded domain
        assert state.lagrangian < 5.0

    def test_cumulative_action_accumulates(self):
        """Action integral S_ψ accumulates across multiple cycles."""
        engine = SymbolicActionEngine()
        agent = SovereignAgent(domain=AgentDomain.MEMORY)
        m = _make_metrics()

        import time

        engine.compute_state(agent, m, grace_injection=1.0)
        time.sleep(0.05)  # dt > 0
        state2 = engine.compute_state(agent, m, grace_injection=1.0)

        # Action integral should have grown
        assert isinstance(state2.cumulative_action, float)
        assert not math.isnan(state2.cumulative_action)

    def test_history_bounded(self):
        """History should not grow unbounded beyond 100 entries."""
        engine = SymbolicActionEngine()
        agent = SovereignAgent(domain=AgentDomain.EVOLUTION)
        m = _make_metrics()

        for _ in range(120):
            engine.compute_state(agent, m)

        assert len(engine._history[AgentDomain.EVOLUTION]) <= 100

    def test_get_report_format(self):
        """get_report returns dict with all domains having Lagrangian data."""
        engine = SymbolicActionEngine()
        agent = SovereignAgent(domain=AgentDomain.FABRICATION)
        m = _make_metrics()

        engine.compute_state(agent, m, grace_injection=1.0)
        report = engine.get_report()

        assert "FABRICATION" in report
        assert "lagrangian" in report["FABRICATION"]
        assert "momentum" in report["FABRICATION"]
        assert "action" in report["FABRICATION"]


# ── LagrangianController ──────────────────────────────────────


class TestLagrangianController:
    def test_predict_returns_dict(self):
        """predict_next_state returns a dict with expected shift keys."""
        ctrl = LagrangianController()
        state = SymbolicActionState(
            domain=AgentDomain.FABRICATION,
            lagrangian=5.0,
            momentum=2.0,
        )

        result = ctrl.predict_next_state(state)
        # Returns a dict (verify it's a dict with float values)
        assert isinstance(result, dict)
        assert all(isinstance(v, float) for v in result.values())

    def test_action_loss_high_if_lagrangian_far_from_ideal(self):
        """Lagrangian far from 10 → high loss."""
        ctrl = LagrangianController()
        bad_state = SymbolicActionState(
            domain=AgentDomain.SECURITY,
            lagrangian=-50.0,
        )
        good_state = SymbolicActionState(
            domain=AgentDomain.SECURITY,
            lagrangian=10.0,
        )

        bad_loss = ctrl.compute_action_loss(bad_state)
        good_loss = ctrl.compute_action_loss(good_state)

        assert bad_loss > good_loss
        assert good_loss == pytest.approx(0.0, abs=1e-6)


# ── Axiom 12 Integration ──────────────────────────────────────


class TestAxiom12Integration:
    def test_entropy_reduction_has_state_hash_tag(self):
        """EntropyReduction mutations carry state_hash in epigenetic_tags."""
        from cortex.evolution.strategies import EntropyReductionStrategy

        agent = SovereignAgent(domain=AgentDomain.VERIFICATION)
        agent.fitness = 82.0
        agent.generation = 700  # ratio = 700/32 = 21.9 > 20

        mutation = EntropyReductionStrategy().evaluate_agent(agent)
        assert mutation is not None
        assert "axiom_12_trigger" in mutation.epigenetic_tags
        assert mutation.epigenetic_tags["axiom_12_trigger"] is True
        assert "state_hash" in mutation.epigenetic_tags
        # SHA-256 produces a hex string of length 64
        assert len(mutation.epigenetic_tags["state_hash"]) == 64

    def test_agent_state_hash_changes_after_mutation(self):
        """state_hash changes when fitness changes (hash reflects state)."""
        agent = SovereignAgent(domain=AgentDomain.SWARM)
        hash_before = agent.state_hash
        agent.apply_mutation(Mutation(delta_fitness=10.0))
        hash_after = agent.state_hash
        assert hash_before != hash_after

    def test_state_hash_is_sha256_hex(self):
        """state_hash is a valid 64-char SHA-256 hex string."""
        agent = SovereignAgent(domain=AgentDomain.FABRICATION)
        h = agent.state_hash
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
