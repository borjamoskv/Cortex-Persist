"""Immortality Index (ι) — Cognitive Crystallization Metric.

Measures the ratio of crystallized cognitive state to estimated total
cognitive activity using Shannon information theory:

    ι = 0.25·δ + 0.25·γ + 0.20·ρ + 0.15·κ + 0.15·σ

Where:
    δ = Diversity   — normalized entropy of fact types
    γ = Continuity  — 1 − (max_gap / total_span)
    ρ = Density     — facts per active day, normalized
    κ = Quality     — confidence-weighted fact ratio
    σ = Coverage    — domain pairs / theoretical max

Scale: 0% (total entropic decay) → 100% (functional immortality).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.shannon.analyzer import normalized_entropy
from cortex.shannon.scanner import MemoryScanner

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["ImmortalityIndex"]

logger = logging.getLogger("cortex.shannon.immortality")

# ── Weights ──────────────────────────────────────────────────────────
_W_DIVERSITY = 0.25
_W_CONTINUITY = 0.25
_W_DENSITY = 0.20
_W_QUALITY = 0.15
_W_COVERAGE = 0.15

# ── Density normalization: 5+ facts/active-day = perfect density ─────
_DENSITY_CAP = 5.0

# ── Thresholds ───────────────────────────────────────────────────────
_THRESHOLD_IMMORTAL = 0.75
_THRESHOLD_PARTIAL = 0.45


def _clamp(value: float) -> float:
    """Clamp to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def _dimension_bar(value: float, width: int = 20) -> str:
    """Unicode bar for a [0, 1] value."""
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _diagnosis(iota: float) -> str:
    """Classify the immortality score."""
    if iota >= _THRESHOLD_IMMORTAL:
        return "approaching_functional_immortality"
    if iota >= _THRESHOLD_PARTIAL:
        return "partial_crystallization"
    return "entropic_decay_risk"


def _diagnosis_badge(iota: float) -> str:
    """Color-coded Rich badge for the index."""
    pct = iota * 100
    if iota >= _THRESHOLD_IMMORTAL:
        return f"[bold green]🟢 ι = {pct:.1f}%[/]"
    if iota >= _THRESHOLD_PARTIAL:
        return f"[bold yellow]🟡 ι = {pct:.1f}%[/]"
    return f"[bold red]🔴 ι = {pct:.1f}%[/]"


def _weakest_dimension(
    dimensions: dict[str, float],
) -> tuple[str, float, str]:
    """Find weakest dimension and return (name, score, recommendation)."""
    recommendations = {
        "diversity": (
            "Memory is dominated by few fact types. "
            "Diversify: cortex store --type decision/error/bridge/ghost"
        ),
        "continuity": (
            "Large temporal gaps detected — periods of cognitive activity "
            "were NOT crystallized. Maintain daily cortex store sessions."
        ),
        "density": (
            "Low crystallization density on active days. "
            "Store more facts per session: decisions, errors, and learnings."
        ),
        "quality": (
            "Low average confidence across facts. "
            "Upgrade hypotheses to verified: cortex update --confidence C4/C5"
        ),
        "coverage": (
            "Knowledge map has gaps — some (type × project) combinations "
            "are empty. Explore cross-domain bridges."
        ),
    }
    name = min(dimensions, key=lambda k: dimensions[k])
    return name, dimensions[name], recommendations.get(name, "")


class ImmortalityIndex:
    """Computes the Immortality Index (ι) from CORTEX memory state.

    The index quantifies how much of a human's cognitive activity
    has been crystallized into the CORTEX ledger, measuring the
    path toward functional informational immortality.
    """

    @staticmethod
    async def compute(
        engine: CortexEngine,
        project: str | None = None,
    ) -> dict:
        """Run the complete immortality analysis.

        Args:
            engine: Active CortexEngine instance.
            project: Optional project filter.

        Returns:
            Structured dict with per-dimension scores, composite ι,
            diagnosis, badge, and recommendation for weakest dimension.
        """
        scanner = MemoryScanner(engine)

        # ── Gather raw data ──────────────────────────────────────
        total = await scanner.total_active_facts(project)
        type_dist = await scanner.type_distribution(project)
        max_gap, total_span, active_days = await scanner.temporal_gap_days(project)
        weighted_sum, conf_total = await scanner.confidence_weight_sum(project)
        filled, theoretical = await scanner.domain_coverage()

        # ── Edge case: empty database ────────────────────────────
        if total == 0:
            return _empty_result(project)

        # ── δ (Diversity) ────────────────────────────────────────
        diversity = _clamp(normalized_entropy(type_dist))

        # ── γ (Continuity) ───────────────────────────────────────
        if total_span > 0 and active_days >= 2:
            continuity = _clamp(1.0 - (max_gap / total_span))
        else:
            continuity = 1.0 if active_days >= 1 else 0.0

        # ── ρ (Density) ──────────────────────────────────────────
        if active_days > 0:
            facts_per_day = total / active_days
            density = _clamp(facts_per_day / _DENSITY_CAP)
        else:
            density = 0.0

        # ── κ (Quality) ──────────────────────────────────────────
        quality = _clamp(weighted_sum / conf_total)

        # ── σ (Coverage) ─────────────────────────────────────────
        coverage = _clamp(filled / theoretical)

        # ── Composite ι ──────────────────────────────────────────
        iota = (
            _W_DIVERSITY * diversity
            + _W_CONTINUITY * continuity
            + _W_DENSITY * density
            + _W_QUALITY * quality
            + _W_COVERAGE * coverage
        )
        iota = _clamp(iota)

        dimensions = {
            "diversity": diversity,
            "continuity": continuity,
            "density": density,
            "quality": quality,
            "coverage": coverage,
        }

        weak_name, weak_score, weak_rec = _weakest_dimension(dimensions)

        return {
            "iota": round(iota, 4),
            "iota_pct": round(iota * 100, 1),
            "diagnosis": _diagnosis(iota),
            "badge": _diagnosis_badge(iota),
            "total_facts": total,
            "active_days": active_days,
            "total_span_days": round(total_span, 1),
            "max_gap_days": round(max_gap, 1),
            "project_filter": project,
            "dimensions": {
                name: {
                    "score": round(val, 4),
                    "pct": round(val * 100, 1),
                    "bar": _dimension_bar(val),
                    "weight": w,
                }
                for name, val, w in [
                    ("diversity", diversity, _W_DIVERSITY),
                    ("continuity", continuity, _W_CONTINUITY),
                    ("density", density, _W_DENSITY),
                    ("quality", quality, _W_QUALITY),
                    ("coverage", coverage, _W_COVERAGE),
                ]
            },
            "weakest": {
                "dimension": weak_name,
                "score": round(weak_score, 4),
                "recommendation": weak_rec,
            },
        }


def _empty_result(project: str | None) -> dict:
    """Return a zeroed-out result for an empty database."""
    zero_dim = {
        name: {"score": 0.0, "pct": 0.0, "bar": _dimension_bar(0.0), "weight": w}
        for name, w in [
            ("diversity", _W_DIVERSITY),
            ("continuity", _W_CONTINUITY),
            ("density", _W_DENSITY),
            ("quality", _W_QUALITY),
            ("coverage", _W_COVERAGE),
        ]
    }
    return {
        "iota": 0.0,
        "iota_pct": 0.0,
        "diagnosis": "entropic_decay_risk",
        "badge": _diagnosis_badge(0.0),
        "total_facts": 0,
        "active_days": 0,
        "total_span_days": 0.0,
        "max_gap_days": 0.0,
        "project_filter": project,
        "dimensions": zero_dim,
        "weakest": {
            "dimension": "diversity",
            "score": 0.0,
            "recommendation": "No facts stored. Begin crystallization: cortex store",
        },
    }
