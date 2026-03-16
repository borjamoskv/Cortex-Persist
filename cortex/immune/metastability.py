"""Metastability Probing — Axiom Ω₁₃ Immune System Upgrade.

Detects systems that appear stable only because nobody has perturbed them.
"No anomalies detected" ≠ "stable" — absence of perturbation is not
evidence of stability.

Status: IMPLEMENTED (upgraded from PARTIAL via Ω₁₃ enforcement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

__all__ = [
    "MetastabilityReport",
    "assess_metastability",
]

logger = logging.getLogger("cortex.immune.metastability")

# ── Heuristic weights ────────────────────────────────────────────────
# Sum to 1.0. Each signal contributes independently.

_W_COVERAGE = 0.30
_W_SINGLE_POINT = 0.20
_W_UNTESTED_FALLBACK = 0.20
_W_IMPLICIT_CONFIG = 0.15
_W_SILENT_FAILURE = 0.15

# Threshold: score ≥ 0.45 → fragile metastable state
_FRAGILE_THRESHOLD = 0.45
_CONFIDENCE_PENALTY = 0.2


@dataclass
class MetastabilityReport:
    """Result of a metastability probe on a subsystem.

    Attributes:
        subsystem: Name of the subsystem probed.
        fragile_stable_state: True if the system is in metastable equilibrium.
        hidden_dependency_score: Composite fragility score (0.0–1.0).
        perturbation_needed: Whether the system needs active perturbation testing.
        confidence_penalty: Penalty to apply to system confidence (0.0 if stable).
        reasons: Human-readable list of fragility indicators detected.
    """

    subsystem: str
    fragile_stable_state: bool
    hidden_dependency_score: float
    perturbation_needed: bool
    confidence_penalty: float
    reasons: list[str] = field(default_factory=list)


def assess_metastability(
    subsystem: str = "default",
    *,
    coverage_hot_paths: float = 1.0,
    single_point_dependencies: int = 0,
    untested_fallbacks: int = 0,
    config_implicit: bool = False,
    silent_failure_history: int = 0,
) -> MetastabilityReport:
    """Probe a subsystem for metastable fragility.

    Five independent signals contribute to a composite score.
    If the score ≥ 0.45, the subsystem is declared fragile-stable
    and receives a confidence penalty.

    Args:
        subsystem: Subsystem identifier.
        coverage_hot_paths: Test coverage on hot paths (0.0–1.0).
        single_point_dependencies: Number of SPOF dependencies.
        untested_fallbacks: Number of fallback paths without tests.
        config_implicit: Whether configuration is implicit/unversioned.
        silent_failure_history: Number of historically silent failures.

    Returns:
        MetastabilityReport with fragility assessment.
    """
    score = 0.0
    reasons: list[str] = []

    if coverage_hot_paths < 0.6:
        score += _W_COVERAGE
        reasons.append(f"low hot-path coverage ({coverage_hot_paths:.0%} < 60%)")

    if single_point_dependencies > 0:
        score += _W_SINGLE_POINT
        reasons.append(f"{single_point_dependencies} single-point dependency(ies)")

    if untested_fallbacks > 0:
        score += _W_UNTESTED_FALLBACK
        reasons.append(f"{untested_fallbacks} untested fallback path(s)")

    if config_implicit:
        score += _W_IMPLICIT_CONFIG
        reasons.append("implicit/unversioned configuration")

    if silent_failure_history > 0:
        score += _W_SILENT_FAILURE
        reasons.append(f"{silent_failure_history} historical silent failure(s)")

    fragile = score >= _FRAGILE_THRESHOLD
    penalty = _CONFIDENCE_PENALTY if fragile else 0.0

    report = MetastabilityReport(
        subsystem=subsystem,
        fragile_stable_state=fragile,
        hidden_dependency_score=round(score, 3),
        perturbation_needed=fragile,
        confidence_penalty=penalty,
        reasons=reasons,
    )

    if fragile:
        logger.warning(
            "Metastable fragility detected in '%s': score=%.3f reasons=%s",
            subsystem,
            score,
            reasons,
        )
    else:
        logger.debug(
            "Subsystem '%s' passes metastability probe: score=%.3f",
            subsystem,
            score,
        )

    return report
