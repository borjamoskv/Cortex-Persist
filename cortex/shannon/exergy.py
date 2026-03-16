"""Exergy Scoring — Axiom Ω₁₃ Shannon Upgrade.

Measures useful extractable work, not just entropy or volume.
"More data" does not imply better exergy_score. Content that is
useful and compressible beats abundant ornamental content.

If exergy_score doesn't affect priority, persistence, or routing,
it's a semáforo pintado en una pared.

Status: IMPLEMENTED (upgraded from DECORATIVE via Ω₁₃ enforcement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

__all__ = [
    "ExergyReport",
    "compute_exergy_report",
]

logger = logging.getLogger("cortex.shannon.exergy")

# ── Formula weights ──────────────────────────────────────────────────
# downstream_utility dominates — if decisions can't use it, it's waste.

_W_UTILITY = 0.35
_W_WORK_RATIO = 0.25
_W_COMPRESSION = 0.20
_W_NOISE = 0.20  # subtracted


@dataclass
class ExergyReport:
    """Result of exergy analysis on a data operation or fact set.

    Attributes:
        entropy_score: Raw Shannon entropy of the data.
        compression_ratio: Real redundancy reduction achieved (0.0–1.0).
        exergy_score: Composite useful work score.
        downstream_utility: How much this enables future decisions (0.0–1.0).
        noise_fraction: Proportion of non-reusable content (0.0–1.0).
        useful_work_ratio: Decisions enabled per token spent.
    """

    entropy_score: float
    compression_ratio: float
    exergy_score: float
    downstream_utility: float
    noise_fraction: float
    useful_work_ratio: float


def compute_exergy_report(
    entropy_score: float,
    compression_ratio: float,
    downstream_utility: float,
    decisions_enabled: int,
    tokens_spent: int,
    noise_fraction: float,
) -> ExergyReport:
    """Compute exergy report — useful work, not raw information volume.

    Formula (pragmatic v1):
        exergy = 0.35*downstream_utility + 0.25*useful_work_ratio
               + 0.20*compression_ratio - 0.20*noise_fraction

    Where: useful_work_ratio = decisions_enabled / tokens_spent

    Args:
        entropy_score: Raw Shannon entropy of the data.
        compression_ratio: Redundancy reduction achieved (0.0–1.0).
        downstream_utility: How much this enables future decisions (0.0–1.0).
        decisions_enabled: Number of decisions or actions enabled.
        tokens_spent: Total tokens or cost units consumed.
        noise_fraction: Proportion of non-reusable content (0.0–1.0).

    Returns:
        ExergyReport with composite score and components.

    Raises:
        ValueError: If tokens_spent <= 0 (division by zero protection).
    """
    if tokens_spent <= 0:
        raise ValueError("tokens_spent must be > 0")

    useful_work_ratio = decisions_enabled / tokens_spent

    exergy_score = (
        _W_UTILITY * downstream_utility
        + _W_WORK_RATIO * useful_work_ratio
        + _W_COMPRESSION * compression_ratio
        - _W_NOISE * noise_fraction
    )

    report = ExergyReport(
        entropy_score=entropy_score,
        compression_ratio=compression_ratio,
        exergy_score=round(exergy_score, 6),
        downstream_utility=downstream_utility,
        noise_fraction=noise_fraction,
        useful_work_ratio=round(useful_work_ratio, 6),
    )

    logger.debug(
        "Exergy computed: score=%.6f utility=%.2f work_ratio=%.6f noise=%.2f",
        report.exergy_score,
        downstream_utility,
        useful_work_ratio,
        noise_fraction,
    )

    return report
