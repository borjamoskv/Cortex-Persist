"""Weighted 0-100 health scoring engine.

Uses sealed Grade enum. Supports configurable weight overrides.
"""

from __future__ import annotations

from cortex.health.models import Grade, HealthScore, MetricSnapshot

# Default metric weights (override via HealthScorer.score(weights=...))
DEFAULT_WEIGHTS: dict[str, float] = {
    "db": 1.5,
    "ledger": 1.2,
    "entropy": 1.0,
    "facts": 0.8,
    "wal": 0.6,
}


class HealthScorer:
    """Computes a weighted 0-100 health score.

    Formula::

      score = Σ(metric.value × weight) / Σ(weight) × 100

    Weight resolution:
      1. Explicit ``weights`` dict (if passed)
      2. Metric's own ``.weight`` attribute
      3. ``DEFAULT_WEIGHTS[metric.name]``
    """

    @staticmethod
    def score(
        metrics: list[MetricSnapshot],
        weights: dict[str, float] | None = None,
    ) -> HealthScore:
        """Compute the aggregate health score."""
        if not metrics:
            return HealthScore(
                score=0.0, grade=Grade.FAILED, metrics=[],
            )

        resolved: list[tuple[MetricSnapshot, float]] = []
        for m in metrics:
            if weights and m.name in weights:
                w = weights[m.name]
            elif m.weight > 0:
                w = m.weight
            else:
                w = DEFAULT_WEIGHTS.get(m.name, 1.0)
            resolved.append((m, w))

        total_weight = sum(w for _, w in resolved)
        if total_weight <= 0:
            return HealthScore(
                score=0.0, grade=Grade.FAILED, metrics=metrics,
            )

        weighted_sum = sum(m.value * w for m, w in resolved)
        raw_score = (weighted_sum / total_weight) * 100.0
        clamped = max(0.0, min(100.0, raw_score))
        grade = Grade.from_score(clamped)

        # Calculate Sub-indices
        sub_indices: dict[str, float] = {}
        mapping = {
            "storage": {"db", "facts"},
            "integrity": {"ledger", "entropy"},
            "performance": {"wal"},
        }
        for name, metrics_in_index in mapping.items():
            idx_metrics = [
                (m, w) for m, w in resolved
                if m.name in metrics_in_index
            ]
            if not idx_metrics:
                continue
            idx_tw = sum(w for _, w in idx_metrics)
            if idx_tw > 0:
                idx_w_sum = sum(m.value * w for m, w in idx_metrics)
                sub_indices[name] = round(idx_w_sum / idx_tw * 100.0, 1)

        return HealthScore(
            score=clamped, grade=grade, metrics=metrics,
            sub_indices=sub_indices,
        )

    @staticmethod
    def classify(score: float) -> Grade:
        """Map a 0-100 score to a sealed Grade."""
        return Grade.from_score(score)

    @staticmethod
    def get_weights() -> dict[str, float]:
        """Return the default metric weight map (copy)."""
        return dict(DEFAULT_WEIGHTS)

    @staticmethod
    def summarize(health: HealthScore) -> str:
        """One-line summary with Sovereign emoji."""
        return (
            f"{health.grade.emoji} CORTEX Health: "
            f"{health.score:.1f}/100 "
            f"(Grade {health.grade.letter})"
        )
