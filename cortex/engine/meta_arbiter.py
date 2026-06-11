# [C5-REAL] Exergy-Maximized
"""CORTEX Meta-Arbiter — Dual-Substrate Arbitration Engine.

Provides two primary executive layers:
1. MetaArbiter (Cognitive Arbitration): Resolves inter-layer contradictions
   using weighted evidence fusion across the cognitive substrates:
     L1: Embedding (semantic similarity signal)
     L2: Topology  (Hodge geodesic potential signal)
     L3: Ledger    (immutable causal truth signal)
     L4: RL        (Shannon gym policy suggestion)
   The Ledger (L3) is sovereign ground truth — no layer can override a ledger fact.

2. MetaArbiterKernel (Thermodynamic Trace Collapse): collapse operator for
   ExecutionTrace objects, as specified in the E1 profiler blueprint.

Reality Level: C5-REAL
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Final, Iterable

from cortex.tools.trace_adapter import ExecutionTrace

logger = logging.getLogger("cortex.engine.meta_arbiter")


# ─── Constants for Cognitive Arbitration ─────────────────────────────

# Default weights for each layer's contribution to the fused signal.
# L3 (Ledger) has veto power and is handled separately.
DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    "L1_EMBEDDING": 0.35,
    "L2_TOPOLOGY": 0.30,
    "L3_LEDGER": 0.0,  # Ledger is boolean gate, not weighted
    "L4_RL": 0.35,
}

# Thresholds
CONFLICT_THRESHOLD: Final[float] = 0.40  # Divergence above this → conflict
CONFIDENCE_FLOOR: Final[float] = 0.25  # Below this → ABSTAIN
LEDGER_VETO_ACTIVE: Final[bool] = True  # L3 can veto all other layers


# ─── Data Structures for Cognitive Arbitration ───────────────────────


class Resolution(Enum):
    """The arbiter's final disposition."""

    CONSENSUS = auto()  # All layers agree (within threshold)
    LEDGER_OVERRIDE = auto()  # Ledger truth overrides probabilistic layers
    WEIGHTED_FUSION = auto()  # Layers disagree; fused by weight
    ABSTAIN = auto()  # Insufficient confidence from all layers
    CONFLICT = auto()  # Irreconcilable divergence; requires human review


class LayerID(Enum):
    L1_EMBEDDING = "L1_EMBEDDING"
    L2_TOPOLOGY = "L2_TOPOLOGY"
    L3_LEDGER = "L3_LEDGER"
    L4_RL = "L4_RL"


@dataclass(frozen=True)
class LayerSignal:
    """A normalized signal from one cognitive layer."""

    layer: LayerID
    score: float  # Normalized [0.0, 1.0] confidence/relevance
    raw_value: Any  # Original value from the layer (for audit)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"[META-ARBITER] LayerSignal score must be in [0,1], got {self.score} "
                f"from {self.layer.value}"
            )


@dataclass(frozen=True)
class ConflictPair:
    """Records a detected contradiction between two layers."""

    layer_a: LayerID
    layer_b: LayerID
    divergence: float  # |score_a - score_b|
    description: str


@dataclass(frozen=True)
class ArbiterVerdict:
    """The canonical output of the Meta-Arbiter."""

    resolution: Resolution
    fused_score: float  # Final arbitrated confidence [0,1]
    winning_layer: LayerID | None  # Which layer dominated (if applicable)
    conflicts: list[ConflictPair]
    layer_signals: dict[str, float]  # Snapshot of all input scores
    audit_hash: str  # SHA-256 of the verdict for ledger tracing
    reasoning: str  # Human-readable justification
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    @property
    def is_actionable(self) -> bool:
        """Whether this verdict provides a clear direction."""
        return self.resolution not in (Resolution.ABSTAIN, Resolution.CONFLICT)


# ─── Cognitive Meta-Arbiter ───────────────────────────────────────────


class MetaArbiter:
    """Cross-layer cognitive arbiter.

    Usage:
        arbiter = MetaArbiter()
        signals = [
            LayerSignal(LayerID.L1_EMBEDDING, 0.85, raw_cosine),
            LayerSignal(LayerID.L2_TOPOLOGY, 0.72, raw_potential),
            LayerSignal(LayerID.L3_LEDGER, 1.0, ledger_verified),
            LayerSignal(LayerID.L4_RL, 0.60, q_value),
        ]
        verdict = arbiter.arbitrate(signals, query_context="memory recall for X")
    """

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

    # ─── Public API ───────────────────────────────────────────────

    def arbitrate(
        self,
        signals: list[LayerSignal],
        query_context: str = "",
    ) -> ArbiterVerdict:
        """Execute cross-layer arbitration.

        Resolution Protocol (in priority order):
        1. If L3 (Ledger) says NO → LEDGER_OVERRIDE (veto)
        2. If all layers below confidence_floor → ABSTAIN
        3. If pairwise divergence > threshold → CONFLICT or WEIGHTED_FUSION
        4. If all layers agree within threshold → CONSENSUS
        """
        self._total_arbitrations += 1
        signal_map = {s.layer: s for s in signals}
        score_map = {s.layer.value: s.score for s in signals}

        logger.info(
            "⚖️ META-ARBITER: Arbitrating %d signals for context '%s'",
            len(signals),
            query_context[:80],
        )

        # ── Phase 0: Empty signals guard ──────────────────────────
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

        # ── Phase 1: Ledger Veto Check ────────────────────────────
        l3 = signal_map.get(LayerID.L3_LEDGER)
        if self._ledger_veto and l3 is not None and l3.score < 0.5:
            logger.warning(
                "🛡️ META-ARBITER: LEDGER VETO — L3 score %.2f < 0.5. "
                "Immutable truth overrides all probabilistic layers.",
                l3.score,
            )
            verdict = ArbiterVerdict(
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
            return verdict

        # ── Phase 2: Confidence Floor Check ───────────────────────
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

        # ── Phase 3: Conflict Detection ───────────────────────────
        conflicts = self._detect_conflicts(probabilistic)
        if conflicts:
            self._total_conflicts += len(conflicts)

        # ── Phase 4: Resolution ───────────────────────────────────
        fused_score = self._weighted_fusion(signals)

        if not conflicts:
            # All layers agree
            resolution = Resolution.CONSENSUS
            winning = self._dominant_layer(signals)
            reasoning = (
                f"Consensus reached. Fused score={fused_score:.3f}. "
                f"Dominant layer: {winning.value}."
            )
        elif any(c.divergence > 0.70 for c in conflicts):
            # Severe divergence — flag for review
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
            # Moderate divergence — resolve by weight
            resolution = Resolution.WEIGHTED_FUSION
            winning = self._dominant_layer(signals)
            reasoning = (
                f"Weighted fusion resolved {len(conflicts)} conflict(s). "
                f"Fused score={fused_score:.3f}. "
                f"Dominant layer: {winning.value}."
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

    # ─── Diagnostics ──────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total_arbitrations": self._total_arbitrations,
            "total_conflicts": self._total_conflicts,
        }

    # ─── Internal Mechanics ───────────────────────────────────────

    def _detect_conflicts(self, signals: list[LayerSignal]) -> list[ConflictPair]:
        """Pairwise divergence detection among probabilistic layers."""
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
        """Compute the weighted average score across all layers."""
        total_weight = 0.0
        weighted_sum = 0.0

        for signal in signals:
            w = self._weights.get(signal.layer.value, 0.0)
            # L3 contributes as a binary gate if present
            if signal.layer == LayerID.L3_LEDGER:
                # Ledger acts as a multiplier, not a weighted term
                continue
            weighted_sum += signal.score * w
            total_weight += w

        if total_weight == 0.0:
            return 0.0

        fused = weighted_sum / total_weight

        # Apply L3 gate: if ledger confidence is high, boost; if low, dampen
        l3 = next(
            (s for s in signals if s.layer == LayerID.L3_LEDGER),
            None,
        )
        if l3 is not None:
            # L3 acts as a confidence multiplier [0.5, 1.0] → [0.5x, 1.0x]
            gate = 0.5 + (l3.score * 0.5)
            fused *= gate

        return min(1.0, max(0.0, fused))

    def _dominant_layer(self, signals: list[LayerSignal]) -> LayerID | None:
        """Find the layer with highest weighted contribution."""
        if not signals:
            return None
        best_layer = signals[0].layer
        best_score = -1.0

        for signal in signals:
            w = self._weights.get(signal.layer.value, 0.0)
            effective = signal.score * w
            if signal.layer == LayerID.L3_LEDGER:
                # Ledger dominance is handled via veto, not weight
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
        """Deterministic hash for ledger tracing of this verdict."""
        payload = json.dumps(
            {"scores": score_map, "context": context},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ─── Thermodynamic Collapse Engine (E1 Blueprint) ──────────────────────


@dataclass(frozen=True)
class TrajectoryScore:
    """Energy breakdown for a single trajectory.

    All components are normalized to [0, 1] where possible.
    The overall `energy` is a weighted sum of the components.
    """

    energy: float
    D_ledger: float
    D_causal: float
    D_consensus: float
    H_branch: float
    D_proj: float
    valid: bool


@dataclass(frozen=True)
class CollapseReceipt:
    """Structured receipt for a collapse decision.

    winning_id: id of the chosen trajectory (or "" if none).
    scores: mapping from trajectory id -> TrajectoryScore.
    state_snapshot: lightweight snapshot of the state associated
                    with this collapse operation.
    eps: numerical tolerance used during selection.
    """

    winning_id: str
    scores: dict[str, TrajectoryScore]
    state_snapshot: Any
    eps: float


class MetaArbiterKernel:
    """Thermodynamic collapse operator over ExecutionTrace.

    This class does not reach into the engine internals directly.
    Instead, it operates over ExecutionTrace objects and opaque
    `state` / `causal_graph` / `vote_ledger` / `replay_engine`
    placeholders, so that callers can progressively wire real
    integrations without breaking the core contract.

    The initial implementation keeps all components trace-local:

    - D_ledger, D_causal, D_consensus, D_proj are 0.0 by default
      (placeholders to be wired to real signals later).
    - H_branch is a simple monotonic function of trace length, acting
      as a proxy for branching/complexity. This makes the operator
      usable in tests and basic profiling without requiring full
      engine wiring.
    """

    def __init__(
        self,
        *,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
        delta: float = 1.0,
        epsilon: float = 1.0,
        eps: float = 1e-6,
    ) -> None:
        # We keep weights explicit for future tuning.
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.delta = float(delta)
        self.epsilon = float(epsilon)
        self.eps = float(eps)

    # ------------------------------------------------------------------
    # Component helpers (trace-local fallbacks)
    # ------------------------------------------------------------------

    def _D_ledger(self, trace: ExecutionTrace, state: Any) -> float:
        """Ledger vs trace inconsistency.

        Placeholder for now: returns 0.0.
        A future version can compare `trace.persisted_events()` with
        the ledger snapshot in `state`.
        """
        return 0.0

    def _D_causal(self, trace: ExecutionTrace, causal_graph: Any) -> float:
        """Causal violation rate.

        Placeholder for now: returns 0.0.
        A future version can query the causal graph for invalid
        edges implied by the trace.
        """
        return 0.0

    def _D_consensus(self, trace: ExecutionTrace, vote_ledger: Any) -> float:
        """Consensus conflict score.

        Placeholder for now: returns 0.0.
        A future version can aggregate disagreement between this
        trajectory and the vote ledger.
        """
        return 0.0

    def _H_branch(self, trace: ExecutionTrace, state: Any) -> float:
        """Branch entropy proxy based on trace length.

        This is *not* the true branching entropy over future
        trajectories, but a monotonic proxy that:
        - is 0.0 for empty traces,
        - grows with the number of events,
        - saturates at 1.0 around 100 events.
        """
        length = trace.length()
        if length <= 0:
            return 0.0
        return min(1.0, length / 100.0)

    def _D_proj(self, trace: ExecutionTrace, state: Any, replay_engine: Any) -> float:
        """Projection error between replayed and actual state.

        Placeholder: returns 0.0 until a stable replay/state-distance
        API is wired in. The signature is kept to match the E1
        specification so callers can start threading a replay_engine
        through the call stack without breaking this module.
        """
        return 0.0

    def _snapshot_state(self, state: Any) -> Any:
        """Lightweight state snapshot for receipts.

        Heuristic:
        - prefer `state.id` if present,
        - else `state.height`,
        - else `hash(state)` or `repr(state)`.
        """
        if hasattr(state, "id"):
            return getattr(state, "id")
        if hasattr(state, "height"):
            return getattr(state, "height")
        try:
            return hash(state)
        except Exception:
            return repr(state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        trace: ExecutionTrace,
        *,
        state: Any,
        causal_graph: Any,
        vote_ledger: Any,
        replay_engine: Any,
    ) -> TrajectoryScore:
        """Compute the E1-style energy and its components for a trace.

        All arguments other than `trace` are kept opaque here to
        avoid coupling this module to specific engine internals.
        """
        d_ledger = self._D_ledger(trace, state)
        d_causal = self._D_causal(trace, causal_graph)
        d_consensus = self._D_consensus(trace, vote_ledger)
        h_branch = self._H_branch(trace, state)
        d_proj = self._D_proj(trace, state, replay_engine)

        energy = (
            self.alpha * d_ledger
            + self.beta * d_causal
            + self.gamma * d_consensus
            + self.delta * h_branch
            + self.epsilon * d_proj
        )

        return TrajectoryScore(
            energy=energy,
            D_ledger=d_ledger,
            D_causal=d_causal,
            D_consensus=d_consensus,
            H_branch=h_branch,
            D_proj=d_proj,
            valid=True,
        )

    def collapse(
        self,
        futures: Iterable[ExecutionTrace],
        *,
        state: Any,
        causal_graph: Any,
        vote_ledger: Any,
        replay_engine: Any,
    ) -> tuple[ExecutionTrace | None, CollapseReceipt]:
        """Collapse a set of candidate trajectories into a single winner.

        Returns the chosen ExecutionTrace (or None if the set is
        empty) and a CollapseReceipt containing the full score
        breakdown for all candidates.
        """
        scores: dict[str, TrajectoryScore] = {}
        candidates: list[ExecutionTrace] = []

        for trace in futures:
            sc = self.score(
                trace,
                state=state,
                causal_graph=causal_graph,
                vote_ledger=vote_ledger,
                replay_engine=replay_engine,
            )
            scores[trace.id] = sc
            if sc.valid:
                candidates.append(trace)

        if not candidates:
            receipt = CollapseReceipt(
                winning_id="",
                scores=scores,
                state_snapshot=self._snapshot_state(state),
                eps=self.eps,
            )
            return None, receipt

        winner = min(candidates, key=lambda t: scores[t.id].energy)
        receipt = CollapseReceipt(
            winning_id=winner.id,
            scores=scores,
            state_snapshot=self._snapshot_state(state),
            eps=self.eps,
        )
        return winner, receipt
