"""ENCB v2 — Resolution Strategies (S0–S3).

Four strategies implementing a common interface:
    S0 — Last-Write-Wins (LWW): baseline miserable
    S1 — RAG Summary Overwrite: majority vote weighted by confidence
    S2 — CRDT-only: convergence without reliability adaptation
    S3 — Cortex: CRDT + LogOP + ATMS-lite + reliability adaptation
"""

from __future__ import annotations


import statistics
from collections import defaultdict
from enum import Enum
from typing import Any

from benchmarks.encb.agents import NodeProfile, update_reliability
from benchmarks.encb.atms import ATMSLite
from benchmarks.encb.belief_object import BeliefType
from benchmarks.encb.logop import (
    robust_scalar_aggregate,
    scored_set_aggregate,
    weighted_logop_binary,
    weighted_logop_categorical,
)


class StrategyID(str, Enum):
    """The four resolution strategies."""

    LWW = "S0_lww"
    RAG = "S1_rag"
    CRDT_ONLY = "S2_crdt_only"
    CORTEX = "S3_cortex"


class PropState:
    """Runtime state for a single proposition during simulation.

    Tracks the current resolved value, confidence, support history,
    and conflict mass.
    """

    __slots__ = (
        "key",
        "belief_type",
        "truth",
        "current_value",
        "confidence",
        "conflict_mass",
        "categories",
        "set_universe",
    )

    def __init__(
        self,
        key: str,
        belief_type: BeliefType,
        truth: Any,
        categories: list[Any] | None = None,
        set_universe: set | None = None,
    ) -> None:
        self.key = key
        self.belief_type = belief_type
        self.truth = truth
        self.current_value: Any = None
        self.confidence: float = 0.0
        self.conflict_mass: float = 0.0
        self.categories = categories or []
        self.set_universe = set_universe or set()

    def is_correct(self) -> bool:
        """Check if current_value matches ground truth."""
        if self.current_value is None:
            return False
        if self.belief_type == BeliefType.BOOLEAN:
            return self.current_value == self.truth
        if self.belief_type == BeliefType.CATEGORICAL:
            return self.current_value == self.truth
        if self.belief_type == BeliefType.SCALAR:
            # Within 10% tolerance
            if self.truth == 0:
                return abs(self.current_value) < 1.0
            return abs(self.current_value - self.truth) / abs(self.truth) < 0.10
        if self.belief_type == BeliefType.SET:
            return set(self.current_value) == set(self.truth)
        return False


# ── Observation Type ──────────────────────────────────────────────────────

Observation = tuple[NodeProfile, Any, float]  # (node, value, confidence)


# ── S0: Last-Write-Wins ──────────────────────────────────────────────────


def resolve_lww(
    state: PropState,
    observations: list[Observation],
    round_idx: int,
) -> None:
    """S0 — Last observation wins. No intelligence."""
    if not observations:
        return
    _, value, conf = observations[-1]
    state.current_value = value
    state.confidence = conf
    state.conflict_mass = _compute_conflict_mass(state, observations)


# ── S1: RAG Summary Overwrite ────────────────────────────────────────────


def resolve_rag(
    state: PropState,
    observations: list[Observation],
    round_idx: int,
) -> None:
    """S1 — Majority vote weighted by confidence. Simulates RAG retrieval."""
    if not observations:
        return

    if state.belief_type == BeliefType.BOOLEAN:
        votes = sum(
            (1.0 if val else -1.0) * conf for _, val, conf in observations
        )
        state.current_value = votes >= 0
        state.confidence = min(0.99, max(0.51, abs(votes) / len(observations)))

    elif state.belief_type == BeliefType.CATEGORICAL:
        tallies: dict[Any, float] = defaultdict(float)
        for _, val, conf in observations:
            tallies[val] += conf
        best = max(tallies, key=lambda k: tallies[k])
        total = sum(tallies.values()) + 1e-9
        state.current_value = best
        state.confidence = tallies[best] / total

    elif state.belief_type == BeliefType.SCALAR:
        values = [val for _, val, _ in observations]
        state.current_value = statistics.median(values)
        state.confidence = 0.6

    elif state.belief_type == BeliefType.SET:
        # Union of all observed sets, threshold by frequency
        elem_count: dict[Any, int] = defaultdict(int)
        for _, val, _ in observations:
            if isinstance(val, set):
                for elem in val:
                    elem_count[elem] += 1
        threshold = len(observations) * 0.3
        state.current_value = {e for e, c in elem_count.items() if c >= threshold}
        state.confidence = 0.6

    state.conflict_mass = _compute_conflict_mass(state, observations)


# ── S2: CRDT-Only ────────────────────────────────────────────────────────


def resolve_crdt_only(
    state: PropState,
    observations: list[Observation],
    round_idx: int,
) -> None:
    """S2 — CRDT convergence without reliability adaptation.

    All nodes have equal weight. Converges deterministically but
    cannot distinguish honest from malicious.
    """
    if not observations:
        return

    if state.belief_type == BeliefType.BOOLEAN:
        votes: dict[bool, float] = defaultdict(float)
        for _, val, conf in observations:
            votes[val] += conf
        best_val = max(votes, key=lambda k: votes[k])
        total = sum(votes.values()) + 1e-9
        state.current_value = best_val
        state.confidence = votes[best_val] / total

    elif state.belief_type == BeliefType.CATEGORICAL:
        tallies: dict[Any, float] = defaultdict(float)
        for _, val, conf in observations:
            tallies[val] += conf
        best = max(tallies, key=lambda k: tallies[k])
        total = sum(tallies.values()) + 1e-9
        state.current_value = best
        state.confidence = tallies[best] / total

    elif state.belief_type == BeliefType.SCALAR:
        values = [val for _, val, _ in observations]
        state.current_value = statistics.median(values)
        confs = [conf for _, _, conf in observations]
        state.confidence = statistics.mean(confs)

    elif state.belief_type == BeliefType.SET:
        elem_count: dict[Any, int] = defaultdict(int)
        for _, val, _ in observations:
            if isinstance(val, set):
                for elem in val:
                    elem_count[elem] += 1
        threshold = len(observations) * 0.3
        state.current_value = {e for e, c in elem_count.items() if c >= threshold}
        state.confidence = 0.6

    state.conflict_mass = _compute_conflict_mass(state, observations)


# ── S3: Cortex (Full Hypervisor) ─────────────────────────────────────────


def resolve_cortex(
    state: PropState,
    observations: list[Observation],
    round_idx: int,
    atms: ATMSLite | None = None,
    use_reliability: bool = True,
    use_atms: bool = True,
    use_freshness: bool = True,
    warmup_rounds: int = 5,
) -> None:
    """S3 — CRDT merge + LogOP + ATMS-lite + reliability adaptation.

    Three-layer architecture:
      Layer 1: CRDT merge (in observations, already pre-merged)
      Layer 2: LogOP belief arbitration (this function)
      Layer 3: ATMS truth maintenance (invalidation)

    During warm-up (first `warmup_rounds` rounds), blends LogOP with
    confidence-weighted majority to avoid noise from uninformative
    reliability scores. After warm-up, full LogOP resolution applies.
    """
    if not observations:
        return

    # Warm-up blending factor: 0.0 at round 0 → 1.0 at warmup_rounds
    alpha = min(1.0, round_idx / max(1, warmup_rounds)) if use_reliability else 1.0

    # Layer 2: LogOP resolution (weighted by alpha during warm-up)
    if state.belief_type == BeliefType.BOOLEAN:
        if alpha < 1.0:
            # Blend: fallback = confidence-weighted majority (like S2)
            votes: dict[bool, float] = defaultdict(float)
            for _, val, conf in observations:
                votes[val] += conf
            fallback_val = max(votes, key=lambda k: votes[k])
            fallback_conf = votes[fallback_val] / (sum(votes.values()) + 1e-9)

        obs_tuples = [
            (val, conf, node.reliability if use_reliability else 0.5)
            for node, val, conf in observations
        ]
        logop_val, logop_prob = weighted_logop_binary(obs_tuples)

        if alpha >= 1.0:
            state.current_value = logop_val
            state.confidence = logop_prob
        else:
            # During warm-up: if fallback and logop agree, use logop.
            # If they disagree, blend confidence toward fallback.
            if logop_val == fallback_val:
                state.current_value = logop_val
                state.confidence = logop_prob
            else:
                state.current_value = fallback_val
                state.confidence = (1.0 - alpha) * fallback_conf + alpha * logop_prob

    elif state.belief_type == BeliefType.CATEGORICAL:
        if alpha < 1.0:
            tallies: dict[Any, float] = defaultdict(float)
            for _, val, conf in observations:
                tallies[val] += conf
            fallback_val = max(tallies, key=lambda k: tallies[k])

        obs_tuples = [
            (val, conf, node.reliability if use_reliability else 0.5)
            for node, val, conf in observations
        ]
        logop_val, logop_conf = weighted_logop_categorical(
            obs_tuples, state.categories
        )

        if alpha >= 1.0:
            state.current_value = logop_val
            state.confidence = logop_conf
        else:
            state.current_value = fallback_val if logop_val != fallback_val else logop_val
            state.confidence = logop_conf

    elif state.belief_type == BeliefType.SCALAR:
        obs_tuples = [
            (val, conf, node.reliability if use_reliability else 0.5)
            for node, val, conf in observations
        ]
        resolved_val, resolved_conf = robust_scalar_aggregate(obs_tuples)
        state.current_value = resolved_val
        state.confidence = resolved_conf

    elif state.belief_type == BeliefType.SET:
        obs_tuples = [
            (val if isinstance(val, set) else set(), conf,
             node.reliability if use_reliability else 0.5, round_idx)
            for node, val, conf in observations
        ]
        resolved_val, resolved_conf = scored_set_aggregate(obs_tuples)
        state.current_value = resolved_val
        state.confidence = resolved_conf

    # Layer 2b: Reliability update (adaptive)
    # Higher learning rate (0.12) for faster differentiation of adversaries
    if use_reliability:
        for node, val, _ in observations:
            was_correct = _observation_matches(state, val)
            node.reliability = update_reliability(
                node.reliability, was_correct, lr=0.12
            )

    # Layer 3: ATMS truth maintenance
    if use_atms and atms is not None:
        belief_id = f"{state.key}:{round_idx}"
        assumption_ids = frozenset(
            f"{node.node_id}:{round_idx}" for node, _, _ in observations
        )
        atms.add_justification(belief_id, assumption_ids)

        # Check for invalidated nodes — if a node has reliability < 0.15,
        # add a nogood for its assumptions
        for node, _, _ in observations:
            if use_reliability and node.reliability < 0.15:
                atms.add_nogood(frozenset({f"{node.node_id}:{round_idx}"}))

    state.conflict_mass = _compute_conflict_mass(state, observations)


# ── Helpers ───────────────────────────────────────────────────────────────


def _compute_conflict_mass(
    state: PropState,
    observations: list[Observation],
) -> float:
    """Fraction of observations that disagree with the resolved value."""
    if not observations:
        return 0.0
    disagreements = sum(
        conf
        for _, val, conf in observations
        if not _values_match(state.belief_type, val, state.current_value)
    )
    return disagreements / max(1, len(observations))


def _values_match(bt: BeliefType, a: Any, b: Any) -> bool:
    """Check if two values match for a given belief type."""
    if a is None or b is None:
        return False
    if bt == BeliefType.BOOLEAN:
        return a == b
    if bt == BeliefType.CATEGORICAL:
        return a == b
    if bt == BeliefType.SCALAR:
        if b == 0:
            return abs(a) < 1.0
        return abs(a - b) / abs(b) < 0.10
    if bt == BeliefType.SET:
        return set(a) == set(b)
    return a == b


def _observation_matches(state: PropState, obs_value: Any) -> bool:
    """Check if an observation matches the ground truth."""
    return _values_match(state.belief_type, obs_value, state.truth)


# ── Dispatcher ────────────────────────────────────────────────────────────

STRATEGY_FN = {
    StrategyID.LWW: resolve_lww,
    StrategyID.RAG: resolve_rag,
    StrategyID.CRDT_ONLY: resolve_crdt_only,
    StrategyID.CORTEX: resolve_cortex,
}
