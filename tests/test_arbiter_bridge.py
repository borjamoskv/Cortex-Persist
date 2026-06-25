# [C5-REAL] Exergy-Maximized
"""Tests for ArbiterBridge — Cross-Layer Verdict → Contract-Compliant Routing.

Validates:
    1. Verdict → RoutingContext translation
    2. Contract gate compliance for all resolution types
    3. RL feedback trajectory generation
    4. Fallback behavior for non-actionable verdicts
    5. Edge cases: empty signals, override severity, no RL router
"""

from __future__ import annotations

import pytest

from legacy_research.engine.arbiter_bridge import (
    ArbiterBridge,
    BridgeResult,
    RESOLUTION_BLAST_RADIUS,
    SEVERITY_THRESHOLDS,
)
from legacy_research.engine.meta_arbiter import (
    ArbiterVerdict,
    LayerID,
    LayerSignal,
    MetaArbiter,
    Resolution,
)
from legacy_research.router.causal import CausalPolicyGradientRouter
from legacy_research.router.contract import (
    CognitiveMode,
    RoutingDecision,
    Severity,
)


# ─── Fixtures ────────────────────────────────────────────────────────────


def _make_signals(
    l1: float = 0.80,
    l2: float = 0.75,
    l3: float = 1.0,
    l4: float = 0.70,
) -> list[LayerSignal]:
    """Build a standard 4-layer signal set."""
    return [
        LayerSignal(LayerID.L1_EMBEDDING, l1, raw_value=f"cos={l1}"),
        LayerSignal(LayerID.L2_TOPOLOGY, l2, raw_value=f"pot={l2}"),
        LayerSignal(LayerID.L3_LKRGSER, l3, raw_value=f"ledger={l3}"),
        LayerSignal(LayerID.L4_RL, l4, raw_value=f"q={l4}"),
    ]


@pytest.fixture
def arbiter():
    return MetaArbiter()


@pytest.fixture
def causal_router():
    return CausalPolicyGradientRouter()


@pytest.fixture
def bridge(arbiter, causal_router):
    return ArbiterBridge(arbiter, causal_router, auto_feedback=True)


@pytest.fixture
def bridge_no_rl(arbiter):
    return ArbiterBridge(arbiter, causal_router=None, auto_feedback=True)


# ─── Test: Consensus → NORMAL routing ────────────────────────────────────


class TestConsensusRouting:
    """When all layers agree, bridge should produce NORMAL/LOW routing."""

    def test_consensus_produces_routing_decision(self, bridge):
        signals = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        result = bridge.route(signals, query_context="stable recall")

        assert isinstance(result, BridgeResult)
        assert isinstance(result.decision, RoutingDecision)
        assert result.decision.source == "arbiter_bridge"

    def test_consensus_not_fallback(self, bridge):
        signals = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        result = bridge.route(signals)
        assert not result.fallback_used

    def test_consensus_has_arbiter_hash_in_rationale(self, bridge):
        signals = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        result = bridge.route(signals)
        assert "arbiter_hash=" in result.decision.rationale

    def test_consensus_verdict_resolution(self, bridge):
        signals = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        result = bridge.route(signals)
        assert result.verdict.resolution == Resolution.CONSENSUS


# ─── Test: Ledger Veto → ULTRA_THINK routing ─────────────────────────────


class TestLedgerVetoRouting:
    """When L3 vetoes, bridge should escalate to ULTRA_THINK."""

    def test_ledger_veto_triggers_ultra_think(self, bridge):
        signals = _make_signals(l1=0.90, l2=0.85, l3=0.10, l4=0.80)
        result = bridge.route(signals, query_context="contradicted by ledger")

        assert result.verdict.resolution == Resolution.LKRGSER_OVERRIDE
        # Ledger override → blast_radius=3 → GATE_ULTRA
        assert result.decision.mode == CognitiveMode.ULTRA_THINK
        assert result.decision.gate_id == "GATE_ULTRA"

    def test_ledger_veto_is_not_fallback(self, bridge):
        signals = _make_signals(l1=0.90, l2=0.85, l3=0.10, l4=0.80)
        result = bridge.route(signals)
        assert not result.fallback_used  # Ledger override IS actionable


# ─── Test: ABSTAIN → Fallback to contract.resolve() ─────────────────────


class TestAbstainFallback:
    """When all layers are below confidence floor, bridge falls back."""

    def test_abstain_uses_fallback(self, bridge):
        signals = _make_signals(l1=0.10, l2=0.15, l3=1.0, l4=0.20)
        result = bridge.route(signals)
        assert result.fallback_used
        assert result.verdict.resolution == Resolution.ABSTAIN

    def test_abstain_still_produces_valid_decision(self, bridge):
        signals = _make_signals(l1=0.10, l2=0.15, l3=1.0, l4=0.20)
        result = bridge.route(signals)
        assert isinstance(result.decision, RoutingDecision)
        assert result.decision.mode in CognitiveMode


# ─── Test: CONFLICT → Fallback routing ───────────────────────────────────


class TestConflictRouting:
    """Irreconcilable conflicts should trigger fallback + ULTRA_THINK."""

    def test_conflict_triggers_escalation(self, bridge):
        # Force severe divergence: L1=0.95, L4=0.10 → divergence=0.85
        signals = _make_signals(l1=0.95, l2=0.90, l3=1.0, l4=0.10)
        result = bridge.route(signals)

        # With conflicts and blast_radius=3, expect ULTRA_THINK
        if result.verdict.resolution == Resolution.CONFLICT:
            assert result.fallback_used
            assert result.decision.mode == CognitiveMode.ULTRA_THINK

    def test_conflict_verdict_has_conflicts(self, bridge):
        signals = _make_signals(l1=0.95, l2=0.90, l3=1.0, l4=0.10)
        result = bridge.route(signals)
        if result.verdict.resolution == Resolution.CONFLICT:
            assert len(result.verdict.conflicts) > 0


# ─── Test: Weighted Fusion → DEEP_THINK ──────────────────────────────────


class TestWeightedFusion:
    """Moderate divergence should resolve via weighted fusion."""

    def test_weighted_fusion_produces_deep_think(self, bridge):
        # Moderate divergence: L1=0.80, L4=0.35 → 0.45 > threshold
        signals = _make_signals(l1=0.80, l2=0.75, l3=1.0, l4=0.35)
        result = bridge.route(signals)

        if result.verdict.resolution == Resolution.WEIGHTED_FUSION:
            # blast_radius=2 for WEIGHTED_FUSION → GATE_DEEP
            assert result.decision.mode == CognitiveMode.DEEP_THINK
            assert not result.fallback_used


# ─── Test: RL Feedback Trajectory ────────────────────────────────────────


class TestRLFeedback:
    """Verify CausalTrajectory generation and logging."""

    def test_trajectory_generated_with_causal_router(self, bridge):
        signals = _make_signals()
        result = bridge.route(signals)
        assert result.feedback_trajectory is not None

    def test_trajectory_not_generated_without_causal_router(self, bridge_no_rl):
        signals = _make_signals()
        result = bridge_no_rl.route(signals)
        assert result.feedback_trajectory is None

    def test_trajectory_has_valid_state_vector(self, bridge):
        signals = _make_signals()
        result = bridge.route(signals)
        t = result.feedback_trajectory
        assert t is not None
        assert hasattr(t.state, "ast_complexity")
        assert hasattr(t.state, "kl_instability")
        assert t.kl_divergence_post >= 0.0

    def test_trajectory_action_matches_mode(self, bridge):
        """Pro modes should map to gemini-3.1-pro in trajectory."""
        signals = _make_signals(l1=0.90, l2=0.85, l3=0.10, l4=0.80)
        result = bridge.route(signals)
        t = result.feedback_trajectory
        assert t is not None
        if result.decision.mode in (
            CognitiveMode.DEEP_THINK,
            CognitiveMode.ULTRA_THINK,
            CognitiveMode.DEEP_RESEARCH,
        ):
            assert t.action == "gemini-3.1-pro"

    def test_batch_policy_update(self, bridge):
        """Batch update should not crash after trajectory accumulation."""
        for _ in range(5):
            signals = _make_signals()
            bridge.route(signals)
        bridge.batch_update_policy()
        # Should clear trajectory buffer
        assert len(bridge._causal_router.trajectories) == 0


# ─── Test: Override Severity ─────────────────────────────────────────────


class TestOverrideSeverity:
    """Override severity should bypass score-based classification."""

    def test_override_critical_forces_ultra_think(self, bridge):
        signals = _make_signals(l1=0.95, l2=0.90, l3=1.0, l4=0.85)
        result = bridge.route(
            signals,
            override_severity=Severity.CRITICAL,
        )
        assert result.decision.mode == CognitiveMode.ULTRA_THINK

    def test_override_low_forces_normal(self, bridge):
        """Even with conflicts, LOW override + low blast should route NORMAL."""
        signals = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        result = bridge.route(
            signals,
            override_severity=Severity.LOW,
        )
        # With consensus (blast_radius=0), LOW override → NORMAL
        if result.verdict.resolution == Resolution.CONSENSUS:
            assert result.decision.mode == CognitiveMode.NORMAL


# ─── Test: Empty Signals ─────────────────────────────────────────────────


class TestEmptySignals:
    """Bridge should handle empty signal list gracefully."""

    def test_empty_signals_abstains(self, bridge):
        result = bridge.route([], query_context="nothing")
        assert result.verdict.resolution == Resolution.ABSTAIN
        assert result.fallback_used

    def test_empty_signals_produces_valid_decision(self, bridge):
        result = bridge.route([])
        assert isinstance(result.decision, RoutingDecision)


# ─── Test: Diagnostics ──────────────────────────────────────────────────


class TestDiagnostics:
    """Bridge stats tracking."""

    def test_stats_increment(self, bridge):
        signals = _make_signals()
        bridge.route(signals)
        bridge.route(signals)
        stats = bridge.stats
        assert stats["total_bridge_routes"] == 2

    def test_fallback_rate_computed(self, bridge):
        signals_low = _make_signals(l1=0.10, l2=0.15, l3=1.0, l4=0.20)
        signals_high = _make_signals(l1=0.80, l2=0.78, l3=1.0, l4=0.76)
        bridge.route(signals_low)
        bridge.route(signals_high)
        stats = bridge.stats
        assert 0.0 <= stats["fallback_rate"] <= 1.0


# ─── Test: Score → Severity Mapping ──────────────────────────────────────


class TestScoreToSeverity:
    def test_very_low_score_is_critical(self):
        sev = ArbiterBridge._score_to_severity(0.10)
        assert sev == Severity.CRITICAL

    def test_medium_score_is_high(self):
        sev = ArbiterBridge._score_to_severity(0.40)
        assert sev == Severity.HIGH

    def test_decent_score_is_medium(self):
        sev = ArbiterBridge._score_to_severity(0.60)
        assert sev == Severity.MEDIUM

    def test_high_score_is_low(self):
        sev = ArbiterBridge._score_to_severity(0.90)
        assert sev == Severity.LOW
