# [C5-REAL] Exergy-Maximized
"""Arbiter-Router Bridge — Cross-Layer Verdict → Contract-Compliant Routing.

Connects the MetaArbiter (cognitive L1-L4 arbitration engine) to the
Router subsystem (contract.py deterministic gates + CausalPolicyGradientRouter).

Data Flow:
    LayerSignal[] → MetaArbiter.arbitrate() → ArbiterVerdict
                                                    ↓
                                          ArbiterBridge.route()
                                                    ↓
                                         RoutingDecision (contract.py)
                                                    ↓
                                     CausalTrajectory (feedback to RL)

Invariants:
    - contract.py precedence gates are ALWAYS respected.
    - Non-actionable verdicts (ABSTAIN, CONFLICT) fall back to contract.resolve().
    - Every bridge routing decision is traceable via audit_hash.

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Final

from babylon60.engine.meta.meta_arbiter import (
    ArbiterVerdict,
    LayerID,
    LayerSignal,
    MetaArbiter,
    Resolution,
)
from babylon60.router.causal import CausalPolicyGradientRouter, CausalTrajectory
from babylon60.router.contract import (
    CognitiveMode,
    InformationState,
    RoutingContext,
    RoutingDecision,
    Severity,
    resolve,
)
from babylon60.router.policy import SignalVector

logger = logging.getLogger("cortex.engine.flow.arbiter_bridge")


# ─── Score → Severity Mapping ────────────────────────────────────────────

# Fused score ranges → severity classification
SEVERITY_THRESHOLDS: Final[list[tuple[float, Severity]]] = [
    (0.25, Severity.CRITICAL),  # fused < 0.25 → catastrophic uncertainty
    (0.50, Severity.HIGH),  # fused < 0.50 → significant divergence
    (0.75, Severity.MEDIUM),  # fused < 0.75 → moderate concern
    (1.01, Severity.LOW),  # fused >= 0.75 → routine
]

# Resolution → blast_radius mapping
RESOLUTION_BLAST_RADIUS: Final[dict[Resolution, int]] = {
    Resolution.CONSENSUS: 0,
    Resolution.LEDGER_OVERRIDE: 3,  # Ledger veto = catastrophic scope
    Resolution.WEIGHTED_FUSION: 2,  # Fusion implies cross-layer impact
    Resolution.ABSTAIN: 1,  # Unknown scope
    Resolution.CONFLICT: 3,  # Irreconcilable = maximum blast
}


# ─── Bridge Output ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class BridgeResult:
    """Complete bridge output: routing decision + arbiter provenance."""

    decision: RoutingDecision
    verdict: ArbiterVerdict
    fallback_used: bool
    feedback_trajectory: CausalTrajectory | None


# ─── Arbiter-Router Bridge ───────────────────────────────────────────────


class ArbiterBridge:
    """
    Translates cross-layer cognitive arbitration into contract-compliant
    routing decisions and feeds observations back into the causal RL policy.

    Usage:
        bridge = ArbiterBridge(arbiter, causal_router)
        signals = [LayerSignal(...), ...]
        result = bridge.route(signals, query_context="recall X")
        # result.decision → RoutingDecision (contract.py compliant)
        # result.feedback_trajectory → CausalTrajectory (logged to RL)
    """

    def __init__(
        self,
        arbiter: MetaArbiter,
        causal_router: CausalPolicyGradientRouter | None = None,
        auto_feedback: bool = True,
    ) -> None:
        self._arbiter = arbiter
        self._causal_router = causal_router
        self._auto_feedback = auto_feedback
        self._total_routes = 0
        self._total_fallbacks = 0

    # ─── Public API ──────────────────────────────────────────────

    def route(
        self,
        signals: list[LayerSignal],
        query_context: str = "",
        override_severity: Severity | None = None,
    ) -> BridgeResult:
        """
        Execute the full arbiter → contract → RL feedback pipeline.

        1. Run MetaArbiter.arbitrate() on input signals
        2. Translate ArbiterVerdict → RoutingContext
        3. Run contract.resolve() for deterministic routing
        4. (Optional) Generate CausalTrajectory feedback for RL
        """
        self._total_routes += 1

        # ── Step 1: Arbitrate ─────────────────────────────────────
        verdict = self._arbiter.arbitrate(signals, query_context)

        logger.info(
            "🌉 BRIDGE: Verdict=%s FusedScore=%.3f Actionable=%s",
            verdict.resolution.name,
            verdict.fused_score,
            verdict.is_actionable,
        )

        # ── Step 2: Translate Verdict → RoutingContext ────────────
        fallback_used = not verdict.is_actionable
        if fallback_used:
            self._total_fallbacks += 1

        routing_ctx = self._verdict_to_context(
            verdict,
            override_severity=override_severity,
        )

        # ── Step 3: Contract Resolution ───────────────────────────
        decision = resolve(routing_ctx)

        # Stamp the source to reflect bridge provenance
        decision = RoutingDecision(
            mode=decision.mode,
            gate_id=decision.gate_id,
            rationale=(
                f"[BRIDGE] {verdict.resolution.name} → {decision.rationale} "
                f"| arbiter_hash={verdict.audit_hash[:12]}"
            ),
            confidence=verdict.fused_score if verdict.is_actionable else decision.confidence,
            source="arbiter_bridge",
        )

        logger.info(
            "🌉 BRIDGE: Decision=%s Gate=%s Confidence=%.3f Fallback=%s",
            decision.mode.value,
            decision.gate_id,
            decision.confidence,
            fallback_used,
        )

        # ── Step 4: RL Feedback ───────────────────────────────────
        trajectory = None
        if self._auto_feedback and self._causal_router is not None:
            trajectory = self._generate_trajectory(verdict, decision, signals)
            self._causal_router.log_trajectory(trajectory)
            logger.debug(
                "🌉 BRIDGE: CausalTrajectory logged (KL=%.3f, Hazard=%.3f)",
                trajectory.kl_divergence_post,
                trajectory.hazard_rate_impact,
            )

        return BridgeResult(
            decision=decision,
            verdict=verdict,
            fallback_used=fallback_used,
            feedback_trajectory=trajectory,
        )

    def batch_update_policy(self) -> None:
        """Trigger a policy gradient update on accumulated trajectories."""
        if self._causal_router is not None:
            self._causal_router.update_causal_policy()

    # ─── Diagnostics ─────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        arbiter_stats = self._arbiter.stats
        return {
            **arbiter_stats,
            "total_bridge_routes": self._total_routes,
            "total_fallbacks": self._total_fallbacks,
            "fallback_rate": (
                self._total_fallbacks / self._total_routes if self._total_routes > 0 else 0.0
            ),
        }

    # ─── Internal Mechanics ──────────────────────────────────────

    def _verdict_to_context(
        self,
        verdict: ArbiterVerdict,
        override_severity: Severity | None = None,
    ) -> RoutingContext:
        """Map ArbiterVerdict → RoutingContext for contract.resolve()."""

        # Severity from fused score
        if override_severity is not None:
            severity = override_severity
        else:
            severity = self._score_to_severity(verdict.fused_score)

        # Blast radius from resolution type
        blast_radius = RESOLUTION_BLAST_RADIUS.get(verdict.resolution, 1)

        # Information state from layer presence
        has_l1 = LayerID.L1_EMBEDDING.value in verdict.layer_signals
        has_l3 = LayerID.L3_LEDGER.value in verdict.layer_signals
        l3_score = verdict.layer_signals.get(LayerID.L3_LEDGER.value, 1.0)

        info_state = InformationState(
            exists_internally=has_l1,  # Embedding found = info exists
            is_reliable=has_l3 and l3_score >= 0.5,  # Ledger verified
            is_current=verdict.fused_score >= 0.50,  # Recency proxy
        )

        return RoutingContext(
            severity=severity,
            blast_radius=blast_radius,
            info_state=info_state,
            intent_text=verdict.reasoning[:200],
            metadata={
                "arbiter_resolution": verdict.resolution.name,
                "arbiter_hash": verdict.audit_hash,
                "conflict_count": len(verdict.conflicts),
            },
        )

    @staticmethod
    def _score_to_severity(fused_score: float) -> Severity:
        """Convert fused confidence score to Severity enum."""
        for threshold, severity in SEVERITY_THRESHOLDS:
            if fused_score < threshold:
                return severity
        return Severity.LOW

    def _generate_trajectory(
        self,
        verdict: ArbiterVerdict,
        decision: RoutingDecision,
        signals: list[LayerSignal],
    ) -> CausalTrajectory:
        """Convert routing outcome into a CausalTrajectory for RL feedback."""

        # Build SignalVector from layer signals
        l1_score = verdict.layer_signals.get(LayerID.L1_EMBEDDING.value, 0.5)
        l2_score = verdict.layer_signals.get(LayerID.L2_TOPOLOGY.value, 0.5)
        l4_score = verdict.layer_signals.get(LayerID.L4_RL.value, 0.5)

        signal_vec = SignalVector(
            ast_complexity=l2_score * 100,  # Topology as complexity proxy
            kl_instability=1.0 - verdict.fused_score,  # Inverse fused = instability
            entropy_score=1.0 - l1_score,  # Inverse embedding = entropy
            cyclomatic_depth=len(verdict.conflicts) * 10.0,
            event_rate=l4_score,
        )

        # Map CognitiveMode → ModelType for trajectory
        action = (
            "gemini-3.1-pro"
            if decision.mode
            in (CognitiveMode.DEEP_THINK, CognitiveMode.ULTRA_THINK, CognitiveMode.DEEP_RESEARCH)
            else "gemini-3.5-flash"
        )

        # KL divergence post = inverse of fused confidence
        kl_post = 1.0 - verdict.fused_score

        # Hazard rate = number of conflicts normalized
        hazard = len(verdict.conflicts) / max(len(signals), 1)

        return CausalTrajectory(
            state=signal_vec,
            action=action,
            kl_divergence_post=kl_post,
            hazard_rate_impact=hazard,
        )
