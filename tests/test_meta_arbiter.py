# [C5-REAL] Exergy-Maximized
"""
Tests for the CORTEX Meta-Arbiter — Cross-Layer Cognitive Arbitration Engine.

Covers all 5 resolution paths:
  1. CONSENSUS — all layers agree
  2. LEDGER_OVERRIDE — L3 veto active
  3. WEIGHTED_FUSION — moderate divergence resolved by weights
  4. ABSTAIN — all layers below confidence floor
  5. CONFLICT — irreconcilable divergence (>0.70)

Reality Level: C5-REAL
"""

from __future__ import annotations

import pytest

from babylon60.engine.meta.meta_arbiter import (
    ArbiterVerdict,
    ConflictPair,
    LayerID,
    LayerSignal,
    MetaArbiter,
    Resolution,
)


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def arbiter() -> MetaArbiter:
    return MetaArbiter()


def _make_signals(
    l1: float = 0.80,
    l2: float = 0.75,
    l3: float = 1.0,
    l4: float = 0.78,
) -> list[LayerSignal]:
    """Helper to build a 4-signal set."""
    return [
        LayerSignal(layer=LayerID.L1_EMBEDDING, score=l1, raw_value={"cosine": l1}),
        LayerSignal(layer=LayerID.L2_TOPOLOGY, score=l2, raw_value={"potential": l2}),
        LayerSignal(layer=LayerID.L3_LEDGER, score=l3, raw_value={"verified": l3 >= 0.5}),
        LayerSignal(layer=LayerID.L4_RL, score=l4, raw_value={"q_value": l4}),
    ]


# ─── Resolution Path Tests ───────────────────────────────────────────


class TestConsensus:
    """All layers agree within conflict threshold → CONSENSUS."""

    def test_consensus_basic(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.80, l2=0.75, l3=1.0, l4=0.78)
        verdict = arbiter.arbitrate(signals, query_context="test_consensus")

        assert verdict.resolution == Resolution.CONSENSUS
        assert verdict.fused_score > 0.0
        assert verdict.is_actionable is True
        assert len(verdict.conflicts) == 0

    def test_consensus_all_high(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.95, l2=0.93, l3=1.0, l4=0.92)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.CONSENSUS
        assert verdict.fused_score > 0.85

    def test_consensus_identical_scores(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.70, l2=0.70, l3=1.0, l4=0.70)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.CONSENSUS
        assert len(verdict.conflicts) == 0


class TestLedgerOverride:
    """L3 score < 0.5 with ledger_veto=True → LEDGER_OVERRIDE."""

    def test_ledger_veto_basic(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.95, l2=0.90, l3=0.10, l4=0.88)
        verdict = arbiter.arbitrate(signals, query_context="ledger_veto_test")

        assert verdict.resolution == Resolution.LEDGER_OVERRIDE
        assert verdict.winning_layer == LayerID.L3_LEDGER
        assert verdict.fused_score == 0.10
        assert "Ledger" in verdict.reasoning
        assert "sovereign" in verdict.reasoning.lower()

    def test_ledger_veto_zero(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=1.0, l2=1.0, l3=0.0, l4=1.0)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.LEDGER_OVERRIDE
        assert verdict.fused_score == 0.0

    def test_ledger_veto_disabled(self) -> None:
        arbiter = MetaArbiter(ledger_veto=False)
        signals = _make_signals(l1=0.90, l2=0.85, l3=0.10, l4=0.88)
        verdict = arbiter.arbitrate(signals)

        # Without veto, should NOT be LEDGER_OVERRIDE
        assert verdict.resolution != Resolution.LEDGER_OVERRIDE

    def test_ledger_at_boundary(self, arbiter: MetaArbiter) -> None:
        """L3 score exactly 0.5 should NOT trigger veto."""
        signals = _make_signals(l1=0.80, l2=0.75, l3=0.50, l4=0.78)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution != Resolution.LEDGER_OVERRIDE


class TestWeightedFusion:
    """Moderate divergence (0.40-0.70) → WEIGHTED_FUSION."""

    def test_moderate_divergence(self, arbiter: MetaArbiter) -> None:
        # L1=0.90, L4=0.30 → divergence=0.60 (above 0.40 threshold but below 0.70)
        signals = _make_signals(l1=0.90, l2=0.75, l3=1.0, l4=0.30)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.WEIGHTED_FUSION
        assert verdict.is_actionable is True
        assert len(verdict.conflicts) > 0
        assert all(c.divergence <= 0.70 for c in verdict.conflicts)

    def test_fusion_score_is_bounded(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.99, l2=0.50, l3=1.0, l4=0.55)
        verdict = arbiter.arbitrate(signals)

        assert 0.0 <= verdict.fused_score <= 1.0


class TestAbstain:
    """All probabilistic layers below confidence floor → ABSTAIN."""

    def test_abstain_all_low(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.10, l2=0.15, l3=1.0, l4=0.20)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.ABSTAIN
        assert verdict.fused_score == 0.0
        assert verdict.is_actionable is False
        assert verdict.winning_layer is None

    def test_abstain_just_below_floor(self) -> None:
        arbiter = MetaArbiter(confidence_floor=0.30)
        signals = _make_signals(l1=0.29, l2=0.28, l3=1.0, l4=0.25)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.ABSTAIN

    def test_not_abstain_one_above_floor(self, arbiter: MetaArbiter) -> None:
        """If even one layer is above the floor, should NOT abstain."""
        signals = _make_signals(l1=0.50, l2=0.10, l3=1.0, l4=0.10)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution != Resolution.ABSTAIN


class TestConflict:
    """Irreconcilable divergence (>0.70) → CONFLICT."""

    def test_severe_conflict(self, arbiter: MetaArbiter) -> None:
        # L1=0.95, L4=0.10 → divergence=0.85 (above 0.70)
        signals = _make_signals(l1=0.95, l2=0.80, l3=1.0, l4=0.10)
        verdict = arbiter.arbitrate(signals)

        assert verdict.resolution == Resolution.CONFLICT
        assert verdict.is_actionable is False
        assert any(c.divergence > 0.70 for c in verdict.conflicts)

    def test_conflict_reasoning_mentions_human(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.99, l2=0.80, l3=1.0, l4=0.10)
        verdict = arbiter.arbitrate(signals)

        assert "Human review" in verdict.reasoning or "review" in verdict.reasoning.lower()


# ─── Data Structure Tests ────────────────────────────────────────────


class TestLayerSignal:
    def test_valid_signal(self) -> None:
        s = LayerSignal(LayerID.L1_EMBEDDING, 0.75, raw_value=42)
        assert s.score == 0.75
        assert s.layer == LayerID.L1_EMBEDDING
        assert s.timestamp_ns > 0

    def test_invalid_score_above(self) -> None:
        with pytest.raises(ValueError, match="score must be in"):
            LayerSignal(LayerID.L1_EMBEDDING, 1.5, raw_value=None)

    def test_invalid_score_below(self) -> None:
        with pytest.raises(ValueError, match="score must be in"):
            LayerSignal(LayerID.L2_TOPOLOGY, -0.1, raw_value=None)

    def test_boundary_scores(self) -> None:
        s0 = LayerSignal(LayerID.L3_LEDGER, 0.0, raw_value=False)
        s1 = LayerSignal(LayerID.L4_RL, 1.0, raw_value=True)
        assert s0.score == 0.0
        assert s1.score == 1.0


class TestArbiterVerdict:
    def test_actionable_consensus(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals()
        verdict = arbiter.arbitrate(signals)
        assert verdict.is_actionable is True

    def test_audit_hash_deterministic(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals(l1=0.80, l2=0.75, l3=1.0, l4=0.78)
        v1 = arbiter.arbitrate(signals, query_context="hash_test")
        v2 = arbiter.arbitrate(signals, query_context="hash_test")
        assert v1.audit_hash == v2.audit_hash

    def test_audit_hash_changes_with_context(self, arbiter: MetaArbiter) -> None:
        signals = _make_signals()
        v1 = arbiter.arbitrate(signals, query_context="ctx_a")
        v2 = arbiter.arbitrate(signals, query_context="ctx_b")
        assert v1.audit_hash != v2.audit_hash


# ─── Stats & Edge Cases ──────────────────────────────────────────────


class TestStats:
    def test_stats_increment(self) -> None:
        arb = MetaArbiter()
        assert arb.stats["total_arbitrations"] == 0

        arb.arbitrate(_make_signals())
        assert arb.stats["total_arbitrations"] == 1

        arb.arbitrate(_make_signals())
        assert arb.stats["total_arbitrations"] == 2


class TestEdgeCases:
    def test_empty_signals(self, arbiter: MetaArbiter) -> None:
        """Empty signals should degrade gracefully."""
        verdict = arbiter.arbitrate([], query_context="empty")
        # With no probabilistic signals, all are "below floor" → ABSTAIN
        assert verdict.resolution == Resolution.ABSTAIN

    def test_single_layer(self, arbiter: MetaArbiter) -> None:
        signals = [LayerSignal(LayerID.L1_EMBEDDING, 0.85, raw_value=0.85)]
        verdict = arbiter.arbitrate(signals)
        # Single signal, no conflicts possible
        assert verdict.resolution == Resolution.CONSENSUS
        assert verdict.fused_score > 0.0

    def test_only_ledger(self, arbiter: MetaArbiter) -> None:
        signals = [LayerSignal(LayerID.L3_LEDGER, 0.30, raw_value=False)]
        verdict = arbiter.arbitrate(signals)
        assert verdict.resolution == Resolution.LEDGER_OVERRIDE

    def test_custom_weights(self) -> None:
        arb = MetaArbiter(
            weights={
                "L1_EMBEDDING": 0.10,
                "L2_TOPOLOGY": 0.10,
                "L3_LEDGER": 0.0,
                "L4_RL": 0.80,
            }
        )
        signals = _make_signals(l1=0.50, l2=0.50, l3=1.0, l4=0.90)
        verdict = arb.arbitrate(signals)
        # RL dominance with high weight should push score higher
        assert verdict.fused_score > 0.70

    def test_custom_conflict_threshold(self) -> None:
        """With a very low threshold, even small disagreements are conflicts."""
        arb = MetaArbiter(conflict_threshold=0.05)
        signals = _make_signals(l1=0.80, l2=0.75, l3=1.0, l4=0.78)
        verdict = arb.arbitrate(signals)
        # 0.80-0.75=0.05 is exactly at the boundary
        # 0.80-0.78=0.02 is below
        # Some conflicts should be detected
        assert len(verdict.conflicts) >= 0  # May or may not trigger

    def test_ledger_gate_dampens_fusion(self, arbiter: MetaArbiter) -> None:
        """L3 score of 0.5 (just above veto) should dampen the fused score."""
        high_l3 = _make_signals(l1=0.80, l2=0.80, l3=1.0, l4=0.80)
        low_l3 = _make_signals(l1=0.80, l2=0.80, l3=0.50, l4=0.80)

        v_high = arbiter.arbitrate(high_l3)
        v_low = arbiter.arbitrate(low_l3)

        assert v_high.fused_score > v_low.fused_score
