"""Open CORTEX — Observability metrics.

Exact formulas from the Open CORTEX Standard v0.1 §7.
All metrics are pure functions — no I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TurnMetrics:
    """Metrics for a single agent turn."""

    # Coverage (§7.1) — weighted by confidence × relevance
    # coverage = Σ(confidence_i × relevance_i) / Σ(relevance_i)
    coverage: float = 0.0

    # Ignored Memory Rate (§7.2)
    # ignored_rate = |ignored| / |recalled|
    ignored_memory_rate: float = 0.0

    # Plan Adherence (§7.3)
    # adherence = |steps_executed| / |steps_planned|
    plan_adherence: float = 0.0

    # Contradiction Rate (§7.4)
    # contradiction = binary per-turn flag
    contradiction_detected: bool = False

    # JOL Calibration (complementary to Brier)
    # jol_calibration = 1 - |JOL_predicted - JOL_actual|
    jol_calibration: float = 0.0


def compute_coverage(
    recalled: list[dict],
    used_ids: set[str],
) -> float:
    """Compute weighted coverage.

    coverage = Σ(confidence_i × relevance_i) / Σ(relevance_i)
    where relevance_i = 1 if memory was used, 0 otherwise.

    Falls back to simple ratio if no confidence data.
    """
    if not recalled:
        return 0.0

    numerator = 0.0
    denominator = 0.0
    for mem in recalled:
        confidence = mem.get("confidence", 1.0)
        relevance = 1.0 if mem.get("memory_id", mem.get("id", "")) in used_ids else 0.0
        numerator += confidence * relevance
        denominator += relevance if relevance > 0 else 0.0

    if denominator == 0.0:
        return 0.0
    return min(1.0, numerator / denominator)


def compute_ignored_memory_rate(
    total_recalled: int,
    total_used: int,
) -> float:
    """Ignored Memory Rate = |ignored| / |recalled|.

    Target: < 0.3 (most recalled should be relevant).
    """
    if total_recalled == 0:
        return 0.0
    ignored = total_recalled - total_used
    return max(0.0, ignored / total_recalled)


def compute_plan_adherence(
    steps_planned: int,
    steps_executed: int,
) -> float:
    """Plan Adherence = |steps_executed| / |steps_planned|.

    Target: > 0.9.
    """
    if steps_planned == 0:
        return 1.0  # No plan = trivially adherent
    return min(1.0, steps_executed / steps_planned)


def compute_brier_score(
    predictions: list[float],
    outcomes: list[bool],
) -> float:
    """Brier Score = (1/N) × Σ(predicted - actual)².

    Lower = better calibrated. Range [0.0, 1.0].
    Returns -1.0 if insufficient data (< 5 samples).
    """
    if len(predictions) < 5 or len(predictions) != len(outcomes):
        return -1.0

    total = sum(
        (pred - (1.0 if actual else 0.0)) ** 2
        for pred, actual in zip(predictions, outcomes, strict=False)
    )
    return total / len(predictions)


def compute_jol_calibration(
    jol_predicted: float,
    jol_actual: float,
) -> float:
    """JOL Calibration = 1 - |JOL_predicted - JOL_actual|.

    Range [0.0, 1.0]. Higher = better calibrated.
    """
    return 1.0 - abs(jol_predicted - jol_actual)


def compute_reconsolidation_latency_s(
    evidence_written_at: float,
    new_canonical_indexed_at: float,
) -> float:
    """Recon Latency = time(new_canonical) - time(evidence_written).

    Target: < 60s online, < 300s batch.
    """
    return max(0.0, new_canonical_indexed_at - evidence_written_at)


# ─── Aggregator ───────────────────────────────────────────────────────


@dataclass
class MetricsAggregator:
    """Accumulates per-turn metrics for session-level reporting."""

    turns: list[TurnMetrics] = field(default_factory=list)
    brier_predictions: list[float] = field(default_factory=list)
    brier_outcomes: list[bool] = field(default_factory=list)

    def record_turn(self, metrics: TurnMetrics) -> None:
        """Record metrics from a single turn."""
        self.turns.append(metrics)

    def record_brier_sample(self, predicted: float, actual: bool) -> None:
        """Add a calibration sample."""
        self.brier_predictions.append(predicted)
        self.brier_outcomes.append(actual)

    @property
    def avg_coverage(self) -> float:
        if not self.turns:
            return 0.0
        return sum(t.coverage for t in self.turns) / len(self.turns)

    @property
    def avg_ignored_rate(self) -> float:
        if not self.turns:
            return 0.0
        return sum(t.ignored_memory_rate for t in self.turns) / len(self.turns)

    @property
    def avg_plan_adherence(self) -> float:
        if not self.turns:
            return 0.0
        return sum(t.plan_adherence for t in self.turns) / len(self.turns)

    @property
    def contradiction_rate(self) -> float:
        """Contradiction Rate = |turns_with_contradictions| / |total_turns|."""
        if not self.turns:
            return 0.0
        contradictions = sum(1 for t in self.turns if t.contradiction_detected)
        return contradictions / len(self.turns)

    @property
    def brier_score(self) -> float:
        return compute_brier_score(self.brier_predictions, self.brier_outcomes)

    def summary(self) -> dict[str, float]:
        """Export all aggregated metrics."""
        return {
            "turns": len(self.turns),
            "avg_coverage": round(self.avg_coverage, 4),
            "avg_ignored_memory_rate": round(self.avg_ignored_rate, 4),
            "avg_plan_adherence": round(self.avg_plan_adherence, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "brier_score": round(self.brier_score, 4),
        }
