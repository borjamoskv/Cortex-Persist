# [C5-REAL] Exergy-Maximized
"""CORTEX Cognitive Arbiter.

Resolves inter-layer contradictions using weighted evidence fusion
across the cognitive substrates (L1, L2, L3, L4).

Reality Level: C5-REAL
"""

from __future__ import annotations

from babylon60.crypto.hash_registry import cortex_hash
import json
import logging
from typing import Final

from cortex.engine.meta.meta_arbiter_types import (
    ArbiterVerdict,
    ConflictPair,
    LayerID,
    LayerSignal,
    Resolution,
)

logger = logging.getLogger("cortex.engine.meta.cognitive_arbiter")

# ─── Constants for Cognitive Arbitration ─────────────────────────────

DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    "L1_EMBEDDING": 0.35,
    "L2_TOPOLOGY": 0.30,
    "L3_LEDGER": 0.0,
    "L4_RL": 0.35,
}

CONFLICT_THRESHOLD: Final[float] = 0.40
CONFIDENCE_FLOOR: Final[float] = 0.25
LEDGER_VETO_ACTIVE: Final[bool] = True


class MetaArbiter:
    """Cross-layer cognitive arbiter."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        conflict_threshold: float = CONFLICT_THRESHOLD,
        confidence_floor: float = CONFIDENCE_FLOOR,
        ledger_veto: bool = LEDGER_VETO_ACTIVE,
    ) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        self._conflict_threshold = conflict_threshold
        self._confidence_floor = confidence_floor
        self._ledger_veto = ledger_veto
        self._total_arbitrations = 0
        self._total_conflicts = 0

    def arbitrate(
        self,
        signals: list[LayerSignal],
        query_context: str = "",
    ) -> ArbiterVerdict:
        self._total_arbitrations += 1
        signal_map = {s.layer: s for s in signals}
        score_map = {s.layer.value: s.score for s in signals}

        logger.info(
            "⚖️ META-ARBITER: Arbitrating %d signals for context '%s'",
            len(signals),
            query_context[:80],
        )

        if not signals:
            return ArbiterVerdict(
                resolution=Resolution.ABSTAIN,
                fused_score=0.0,
                winning_layer=None,
                conflicts=[],
                layer_signals=score_map,
                audit_hash=self._compute_audit_hash(score_map, query_context),
                reasoning="No signals provided. Cannot arbitrate.",
            )

        l3 = signal_map.get(LayerID.L3_LEDGER)
        if self._ledger_veto and l3 is not None and l3.score < 0.5:
            logger.warning(
                "🛡️ META-ARBITER: LEDGER VETO — L3 score %.2f < 0.5. "
                "Immutable truth overrides all probabilistic layers.",
                l3.score,
            )
            return ArbiterVerdict(
                resolution=Resolution.LEDGER_OVERRIDE,
                fused_score=l3.score,
                winning_layer=LayerID.L3_LEDGER,
                conflicts=[],
                layer_signals=score_map,
                audit_hash=self._compute_audit_hash(score_map, query_context),
                reasoning=(
                    f"Ledger (L3) veto active. Score={l3.score:.3f}. "
                    "The immutable causal chain contradicts the probabilistic "
                    "layers. Ledger truth is sovereign."
                ),
            )

        probabilistic = [s for s in signals if s.layer != LayerID.L3_LEDGER]
        if probabilistic and all(s.score < self._confidence_floor for s in probabilistic):
            logger.warning(
                "⚠️ META-ARBITER: ABSTAIN — All probabilistic layers below confidence floor (%.2f).",
                self._confidence_floor,
            )
            return ArbiterVerdict(
                resolution=Resolution.ABSTAIN,
                fused_score=0.0,
                winning_layer=None,
                conflicts=[],
                layer_signals=score_map,
                audit_hash=self._compute_audit_hash(score_map, query_context),
                reasoning=(
                    f"All probabilistic layers below confidence floor "
                    f"({self._confidence_floor}). Insufficient evidence to decide."
                ),
            )

        conflicts = self._detect_conflicts(probabilistic)
        if conflicts:
            self._total_conflicts += len(conflicts)

        fused_score = self._weighted_fusion(signals)

        if not conflicts:
            resolution = Resolution.CONSENSUS
            winning = self._dominant_layer(signals)
            reasoning = (
                f"Consensus reached. Fused score={fused_score:.3f}. "
                f"Dominant layer: {winning.value}."  # type: ignore
            )
        elif any(c.divergence > 0.70 for c in conflicts):
            resolution = Resolution.CONFLICT
            winning = None
            conflict_desc = "; ".join(
                f"{c.layer_a.value}↔{c.layer_b.value}={c.divergence:.2f}" for c in conflicts
            )
            reasoning = (
                f"Irreconcilable conflict detected: [{conflict_desc}]. "
                f"Fused score={fused_score:.3f} is unreliable. "
                "Human review required."
            )
            logger.error("🔥 META-ARBITER: CONFLICT — %s", reasoning)
        else:
            resolution = Resolution.WEIGHTED_FUSION
            winning = self._dominant_layer(signals)
            reasoning = (
                f"Weighted fusion resolved {len(conflicts)} conflict(s). "
                f"Fused score={fused_score:.3f}. "
                f"Dominant layer: {winning.value}."  # type: ignore
            )

        verdict = ArbiterVerdict(
            resolution=resolution,
            fused_score=fused_score,
            winning_layer=winning,
            conflicts=conflicts,
            layer_signals=score_map,
            audit_hash=self._compute_audit_hash(score_map, query_context),
            reasoning=reasoning,
        )

        logger.info(
            "⚖️ META-ARBITER: Resolution=%s FusedScore=%.3f Winner=%s",
            resolution.name,
            fused_score,
            winning.value if winning else "NONE",
        )

        return verdict

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total_arbitrations": self._total_arbitrations,
            "total_conflicts": self._total_conflicts,
        }

    def _detect_conflicts(self, signals: list[LayerSignal]) -> list[ConflictPair]:
        conflicts: list[ConflictPair] = []
        for i, a in enumerate(signals):
            for b in signals[i + 1 :]:
                divergence = abs(a.score - b.score)
                if divergence > self._conflict_threshold:
                    conflicts.append(
                        ConflictPair(
                            layer_a=a.layer,
                            layer_b=b.layer,
                            divergence=divergence,
                            description=(
                                f"{a.layer.value}({a.score:.3f}) vs {b.layer.value}({b.score:.3f})"
                            ),
                        )
                    )
        return conflicts

    def _weighted_fusion(self, signals: list[LayerSignal]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for signal in signals:
            w = self._weights.get(signal.layer.value, 0.0)
            if signal.layer == LayerID.L3_LEDGER:
                continue
            weighted_sum += signal.score * w
            total_weight += w

        if total_weight == 0.0:
            return 0.0

        fused = weighted_sum / total_weight

        l3 = next(
            (s for s in signals if s.layer == LayerID.L3_LEDGER),
            None,
        )
        if l3 is not None:
            gate = 0.5 + (l3.score * 0.5)
            fused *= gate

        return min(1.0, max(0.0, fused))

    def _dominant_layer(self, signals: list[LayerSignal]) -> LayerID | None:
        if not signals:
            return None
        best_layer = signals[0].layer
        best_score = -1.0

        for signal in signals:
            w = self._weights.get(signal.layer.value, 0.0)
            effective = signal.score * w
            if signal.layer == LayerID.L3_LEDGER:
                effective = signal.score * 0.5
            if effective > best_score:
                best_score = effective
                best_layer = signal.layer

        return best_layer

    @staticmethod
    def _compute_audit_hash(
        score_map: dict[str, float],
        context: str,
    ) -> str:
        payload = json.dumps(
            {"scores": score_map, "context": context},
            sort_keys=True,
        )
        return cortex_hash(payload.encode("utf-8"))
