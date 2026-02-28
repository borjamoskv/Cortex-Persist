"""Entropy Report — Structured analysis of CORTEX memory health.

Orchestrates MemoryScanner (data extraction) and analyzer (pure math)
into a single diagnostic report with actionable recommendations
and a composite health score.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.shannon.analyzer import (
    max_entropy,
    mutual_information,
    normalized_entropy,
    redundancy,
    shannon_entropy,
)
from cortex.shannon.scanner import MemoryScanner

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["EntropyReport"]

logger = logging.getLogger("cortex.shannon")

# Diagnosis thresholds (normalized entropy)
_THRESHOLD_CONCENTRATED = 0.3
_THRESHOLD_FRAGMENTED = 0.9
_THRESHOLD_STALE = 0.3
_THRESHOLD_REDUNDANT = 0.7  # redundancy > 70% is problematic

# Health score weights (must sum to 1.0)
_WEIGHTS = {
    "type": 0.30,
    "age": 0.20,
    "project": 0.15,
    "source": 0.15,
    "redundancy": 0.10,
    "content": 0.10,
}


def _entropy_block(distribution: dict[str, int]) -> dict:
    """Build an entropy analysis block for a single dimension."""
    h = shannon_entropy(distribution)
    h_max = max_entropy(len(distribution))
    norm = normalized_entropy(distribution)
    r = redundancy(distribution)
    return {
        "H": round(h, 4),
        "H_max": round(h_max, 4),
        "normalized": round(norm, 4),
        "redundancy": round(r, 4),
        "categories": len(distribution),
        "distribution": distribution,
    }


def _compute_health(
    type_norm: float,
    age_norm: float,
    proj_norm: float,
    source_norm: float,
    type_redundancy: float,
    content_norm: float,
) -> int:
    """Compute composite health score ∈ [0, 100].

    Higher = healthier memory. Each dimension contributes proportionally:
    - type_norm: diversity of fact types
    - age_norm: temporal spread
    - proj_norm: cross-project balance
    - source_norm: source diversity
    - type_redundancy: penalizes concentration (inverted)
    - content_norm: content length diversity
    """
    raw = (
        _WEIGHTS["type"] * type_norm
        + _WEIGHTS["age"] * age_norm
        + _WEIGHTS["project"] * proj_norm
        + _WEIGHTS["source"] * source_norm
        + _WEIGHTS["redundancy"] * (1.0 - type_redundancy)
        + _WEIGHTS["content"] * content_norm
    )
    return max(0, min(100, round(raw * 100)))


def _detect_trend(velocity: dict[str, int]) -> str:
    """Detect temporal trend from daily fact velocity.

    Compares last 7 days average to overall 30-day average.
    Returns: "growing", "stable", or "declining".
    """
    if len(velocity) < 2:
        return "stable"

    sorted_days = sorted(velocity.keys())
    all_counts = [velocity[d] for d in sorted_days]
    avg_all = sum(all_counts) / len(all_counts)

    # Last 7 entries (or all if < 7)
    recent = all_counts[-7:]
    avg_recent = sum(recent) / len(recent)

    if avg_all < 0.01:
        return "stable"

    ratio = avg_recent / avg_all
    if ratio > 1.3:
        return "growing"
    if ratio < 0.7:
        return "declining"
    return "stable"


def _diagnose(
    type_norm: float,
    age_norm: float,
    type_redundancy: float,
    trend: str,
) -> tuple[str, list[str]]:
    """Determine diagnosis and generate actionable recommendations."""
    diagnosis = "balanced"
    recommendations: list[str] = []

    if type_norm < _THRESHOLD_CONCENTRATED:
        diagnosis = "concentrated"
        recommendations.append(
            "Memory is dominated by a single fact_type. "
            "Diversify with: cortex store --type decision/error/bridge"
        )
    elif type_norm > _THRESHOLD_FRAGMENTED:
        diagnosis = "fragmented"
        recommendations.append(
            "Fact types are extremely spread out. "
            "Focus on core types relevant to active projects."
        )

    if type_redundancy > _THRESHOLD_REDUNDANT:
        if diagnosis == "balanced":
            diagnosis = "redundant"
        recommendations.append(
            f"Redundancy at {type_redundancy:.0%} — too much repetition. "
            "Run: cortex prune --dedup to remove near-duplicates."
        )

    if age_norm < _THRESHOLD_STALE:
        if diagnosis == "balanced":
            diagnosis = "stale"
        recommendations.append(
            "Most facts are from the same time period. "
            "Ensure regular knowledge refresh with daily cortex store sessions."
        )

    if trend == "declining":
        if diagnosis == "balanced":
            diagnosis = "declining"
        recommendations.append(
            "Fact velocity is dropping — memory is going cold. "
            "Re-engage: store recent decisions and learnings."
        )

    if not recommendations:
        recommendations.append(
            "Memory distribution looks healthy. "
            "Continue maintaining diversity across types, projects, and time."
        )

    return diagnosis, recommendations


class EntropyReport:
    """Orchestrates a full Shannon entropy analysis of CORTEX memory."""

    @staticmethod
    async def analyze(
        engine: CortexEngine,
        project: str | None = None,
    ) -> dict:
        """Run complete entropy analysis and return structured results.

        Args:
            engine: Active CortexEngine instance.
            project: Optional project filter. None = all projects.

        Returns:
            Dict with per-dimension entropy, health score, trend,
            mutual information, diagnosis, and recommendations.
        """
        scanner = MemoryScanner(engine)

        # Gather all distributions (sequential for SQLite safety)
        total = await scanner.total_active_facts(project)
        type_dist = await scanner.type_distribution(project)
        conf_dist = await scanner.confidence_distribution(project)
        source_dist = await scanner.source_distribution(project)
        age_dist = await scanner.age_distribution(project)
        content_dist = await scanner.content_length_distribution(project)
        velocity = await scanner.temporal_velocity(project)

        # Project distribution only makes sense without project filter
        if project is None:
            proj_dist = await scanner.project_distribution()
            joint = await scanner.type_project_joint()
            mi = mutual_information(joint)
        else:
            proj_dist = {}
            mi = 0.0

        # Compute entropy blocks
        type_block = _entropy_block(type_dist)
        conf_block = _entropy_block(conf_dist)
        proj_block = _entropy_block(proj_dist)
        source_block = _entropy_block(source_dist)
        age_block = _entropy_block(age_dist)
        content_block = _entropy_block(content_dist)

        # Trend and health
        trend = _detect_trend(velocity)
        type_r = type_block["redundancy"]

        health = _compute_health(
            type_norm=type_block["normalized"],
            age_norm=age_block["normalized"],
            proj_norm=proj_block["normalized"],
            source_norm=source_block["normalized"],
            type_redundancy=type_r,
            content_norm=content_block["normalized"],
        )

        # Diagnose with enriched inputs
        diagnosis, recommendations = _diagnose(
            type_block["normalized"],
            age_block["normalized"],
            type_r,
            trend,
        )

        return {
            "total_facts": total,
            "health_score": health,
            "project_filter": project,
            "temporal_trend": trend,
            "velocity_per_day": velocity,
            "type_entropy": type_block,
            "confidence_entropy": conf_block,
            "project_entropy": proj_block,
            "source_entropy": source_block,
            "age_entropy": age_block,
            "content_entropy": content_block,
            "mutual_info_type_project": round(mi, 4),
            "diagnosis": diagnosis,
            "recommendations": recommendations,
        }
