"""ENCB v2 — Formal Metrics.

Four metrics that measure epistemic debt, not just accuracy:

    PFBR — Persistent False Belief Rate
    TER  — Time to Epistemic Recovery
    EDI  — Epistemic Debt Integral
    CNCL — Corrupt Node Containment Latency
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmarks.encb.agents import NodeProfile, AdversaryType
from benchmarks.encb.belief_object import BeliefType
from benchmarks.encb.strategies import PropState


# ── PFBR — Persistent False Belief Rate ──────────────────────────────────


def pfbr(states: list[PropState]) -> float:
    """Fraction of propositions with incorrect current values.

    PFBR(T) = |{p ∈ P: ŷ_p(T)=1 ∧ y_p=0}| / |P|

    Returns value in [0, 1]. Lower is better.
    """
    if not states:
        return 0.0
    errors = sum(1 for s in states if not s.is_correct())
    return errors / len(states)


# ── TER — Time to Epistemic Recovery ─────────────────────────────────────


def ter(
    round_snapshots: list[list[PropState]],
    alpha: float = 0.90,
    beta: float = 0.90,
    gamma: float = 0.10,
) -> int | None:
    """Number of rounds until recovery thresholds are met.

    Recovery = precision >= α AND recall >= β AND avg_conflict_mass <= γ

    Args:
        round_snapshots: List of [PropState] snapshots per round.
        alpha: Required precision threshold.
        beta: Required recall threshold.
        gamma: Maximum acceptable conflict mass.

    Returns:
        Round index at which recovery was achieved, or None if never.
    """
    for t, states in enumerate(round_snapshots):
        if not states:
            continue

        correct = sum(1 for s in states if s.is_correct())
        total = len(states)

        precision = correct / total if total > 0 else 0.0
        recall = correct / total if total > 0 else 0.0  # same pool, so recall = precision
        avg_conflict = sum(s.conflict_mass for s in states) / total if total > 0 else 1.0

        if precision >= alpha and recall >= beta and avg_conflict <= gamma:
            return t

    return None


# ── EDI — Epistemic Debt Integral ────────────────────────────────────────


def edi(
    round_snapshots: list[list[PropState]],
    w_fp: float = 1.0,
    w_fn: float = 1.0,
    w_conflict: float = 0.25,
) -> float:
    """Cumulative area under the epistemic error curve.

    EDI = Σ_t (w_f · FP_t + w_n · FN_t + w_c · C_t)

    Lower is better. A system that recovers faster has lower EDI.
    """
    total = 0.0

    for states in round_snapshots:
        fp = 0
        fn = 0
        conflict_sum = 0.0

        for s in states:
            if s.current_value is None:
                fn += 1
                continue
            if not s.is_correct():
                # FP = system believes something false
                fp += 1
            # FN = system has no belief about a true proposition
            # (covered by current_value == None above)
            conflict_sum += s.conflict_mass

        total += (w_fp * fp) + (w_fn * fn) + (w_conflict * conflict_sum)

    return total


# ── CNCL — Corrupt Node Containment Latency ──────────────────────────────


def cncl(
    reliability_history: dict[str, list[float]],
    nodes: list[NodeProfile],
    threshold: float = 0.20,
) -> dict[str, int | None]:
    """Per-adversary: rounds until reliability drops below threshold.

    Args:
        reliability_history: node_id → list of reliability per round.
        nodes: All node profiles (to identify adversary type).
        threshold: Reliability threshold for "contained".

    Returns:
        node_id → round of containment (None if never contained).
    """
    # Only measure for corrupt nodes
    corrupt_nodes = {
        n.node_id: n
        for n in nodes
        if n.adversary_type != AdversaryType.HONEST
    }

    result: dict[str, int | None] = {}
    for node_id, profile in corrupt_nodes.items():
        history = reliability_history.get(node_id, [])
        contained_at = None
        for t, rel in enumerate(history):
            if rel < threshold:
                contained_at = t
                break
        result[node_id] = contained_at

    return result


def cncl_avg(containment: dict[str, int | None]) -> float | None:
    """Average containment latency across all corrupt nodes.

    Returns None if no corrupt nodes were ever contained.
    """
    latencies = [v for v in containment.values() if v is not None]
    if not latencies:
        return None
    return sum(latencies) / len(latencies)


# ── Aggregate Report ─────────────────────────────────────────────────────


@dataclass
class MetricsReport:
    """Aggregate metrics for a single strategy run."""

    strategy: str
    seed: int
    pfbr_final: float
    ter_round: int | None
    edi_total: float
    cncl_avg: float | None
    avg_conflict_mass: float
    avg_reliability: float
    error_rate_by_type: dict[str, float]


def compute_report(
    strategy: str,
    seed: int,
    final_states: list[PropState],
    round_snapshots: list[list[PropState]],
    reliability_history: dict[str, list[float]],
    nodes: list[NodeProfile],
) -> MetricsReport:
    """Compute all metrics and return a structured report."""
    containment = cncl(reliability_history, nodes)

    # Error rate by type
    type_errors: dict[str, list[bool]] = {}
    for s in final_states:
        bt = s.belief_type.value
        if bt not in type_errors:
            type_errors[bt] = []
        type_errors[bt].append(s.is_correct())
    error_by_type = {
        bt: 1.0 - (sum(correct_list) / len(correct_list))
        for bt, correct_list in type_errors.items()
    }

    return MetricsReport(
        strategy=strategy,
        seed=seed,
        pfbr_final=pfbr(final_states),
        ter_round=ter(round_snapshots),
        edi_total=edi(round_snapshots),
        cncl_avg=cncl_avg(containment),
        avg_conflict_mass=(
            sum(s.conflict_mass for s in final_states) / len(final_states)
            if final_states else 0.0
        ),
        avg_reliability=(
            sum(n.reliability for n in nodes) / len(nodes)
            if nodes else 0.0
        ),
        error_rate_by_type=error_by_type,
    )
