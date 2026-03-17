"""Cognitive Fingerprint — Preference Model Builder.

Consumes raw data from FingerprintScanner and produces a
CognitiveFingerprint: the compressed representation of a human's
decision-making patterns extracted from the CORTEX Ledger.

This is the core transformation: raw fact distributions →
behavioral archetypes that agents can use as priors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

from cortex.extensions.fingerprint.models import (
    CognitiveFingerprint,
    DomainPreference,
    PatternVector,
)
from cortex.extensions.fingerprint.scanner import FingerprintScanner

__all__ = ["FingerprintExtractor"]

logger = logging.getLogger("cortex.extensions.fingerprint")

# Normalization caps
_SESSION_DENSITY_CAP = 10.0  # 10 facts/day = maximum density
_DEPTH_CAP = 500.0  # 500 chars avg = maximum depth
_BREADTH_CAP = 20.0  # 20 distinct projects = fully polymath

# Archetype decision boundaries (risk_tolerance, synthesis_drive, caution_index)
_ARCHETYPES: list[tuple[str, dict]] = [
    ("sovereign_architect", {"synthesis_drive": 0.2, "breadth": 0.5, "risk_tolerance": 0.5}),
    ("obsessive_executor", {"synthesis_drive": 0.0, "session_density": 0.6, "caution_index": 0.15}),
    ("cautious_guardian", {"risk_tolerance": 0.0, "caution_index": 0.25}),
    ("bold_experimenter", {"risk_tolerance": 0.6, "caution_index": 0.0}),
    ("deep_specialist", {"breadth": 0.0, "depth_preference": 0.5}),
    ("polymath_synthesizer", {"breadth": 0.6, "synthesis_drive": 0.15}),
    ("dormant_archivist", {"recency_bias": 0.0, "session_density": 0.0}),
]


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _classify_archetype(
    pattern: PatternVector,
) -> tuple[str, float]:
    """Match pattern to closest archetype using L1 distance."""
    pattern_dict = {
        "risk_tolerance": pattern.risk_tolerance,
        "caution_index": pattern.caution_index,
        "synthesis_drive": pattern.synthesis_drive,
        "session_density": pattern.session_density,
        "recency_bias": pattern.recency_bias,
        "breadth": pattern.breadth,
        "depth_preference": pattern.depth_preference,
    }

    best_name = "emergent"
    best_score = -1.0

    for name, thresholds in _ARCHETYPES:
        # Score = average dimension match (how well this pattern fits)
        score = 0.0
        for dim, threshold in thresholds.items():
            val = pattern_dict.get(dim, 0.0)
            if threshold >= 0.3:
                score += val / len(thresholds)  # Higher is better
            else:
                score += (1.0 - val) / len(thresholds)  # Lower is better

        if score > best_score:
            best_score = score
            best_name = name

    # Confidence = how far best_score is from 0.5 baseline
    confidence = _clamp(abs(best_score - 0.5) * 2.0)
    return best_name, confidence


def _fingerprint_completeness(total_facts: int, active_domains: int) -> float:
    """Estimate how complete the fingerprint is based on data volume."""
    fact_score = _clamp(total_facts / 100.0)  # 100 facts = 100%
    domain_score = _clamp(active_domains / 10.0)  # 10 domains = 100%
    return round((fact_score * 0.7) + (domain_score * 0.3), 3)


class FingerprintExtractor:
    """Extracts the CognitiveFingerprint from CORTEX memory."""

    @staticmethod
    async def extract(
        engine: CortexEngine,
        project: Optional[str] = None,
        top_domains: int = 15,
    ) -> CognitiveFingerprint:
        """Run the full fingerprint extraction pipeline.

        Args:
            engine: Active CortexEngine instance.
            project: Optional project filter.
            top_domains: Max domain preferences to include.

        Returns:
            CognitiveFingerprint with pattern vector, domain preferences,
            archetype classification, and agent prompt injection ready.
        """
        scanner = FingerprintScanner(engine)

        # ── Gather raw data ──────────────────────────────────────────
        total = await scanner.total_facts(project)

        if total == 0:
            return _empty_fingerprint(project)

        type_dist = await scanner.fact_type_distribution(project)
        conf_dist = await scanner.confidence_distribution(project)
        n_projects = await scanner.distinct_projects()
        avg_len = await scanner.avg_content_length(project)
        recent_count, total_count = await scanner.recency_ratio(project)
        n_active_days, _ = await scanner.active_days(project)
        domain_profiles = await scanner.domain_profiles(project, top_n=top_domains)
        weekly_velocity = await scanner.weekly_velocity_per_domain(project)

        # ── PatternVector computation ────────────────────────────────

        # Risk tolerance: ratio of C3/C4/C5 vs total
        high_conf = sum(conf_dist.get(c, 0) for c in ("C3", "C4", "C5"))
        risk_tolerance = _clamp(high_conf / max(total, 1))

        # Caution index: ratio of error + ghost facts
        caution_types = type_dist.get("error", 0) + type_dist.get("ghost", 0)
        caution_index = _clamp(caution_types / max(total, 1))

        # Synthesis drive: ratio of bridge + discovery facts
        bridge_types = type_dist.get("bridge", 0) + type_dist.get("discovery", 0)
        synthesis_drive = _clamp(bridge_types / max(total, 1))

        # Session density: facts per active day (capped at _SESSION_DENSITY_CAP)
        facts_per_day = total / max(n_active_days, 1)
        session_density = _clamp(facts_per_day / _SESSION_DENSITY_CAP)

        # Recency bias: facts in last 30 days vs total
        recency_bias = _clamp(recent_count / max(total_count, 1))

        # Breadth: distinct projects (capped at _BREADTH_CAP)
        breadth = _clamp(n_projects / _BREADTH_CAP)

        # Depth preference: avg content length (capped at _DEPTH_CAP)
        depth_preference = _clamp(avg_len / _DEPTH_CAP)

        pattern = PatternVector(
            risk_tolerance=round(risk_tolerance, 4),
            caution_index=round(caution_index, 4),
            synthesis_drive=round(synthesis_drive, 4),
            session_density=round(session_density, 4),
            recency_bias=round(recency_bias, 4),
            breadth=round(breadth, 4),
            depth_preference=round(depth_preference, 4),
        )

        # ── Domain preferences ───────────────────────────────────────
        domain_prefs: list[DomainPreference] = []
        for dp in domain_profiles:
            vel = weekly_velocity.get((dp["project"], dp["fact_type"]), 0.0)
            domain_prefs.append(
                DomainPreference(
                    project=dp["project"],
                    fact_type=dp["fact_type"],
                    count=dp["count"],
                    avg_confidence_weight=round(dp["avg_confidence_weight"], 3),
                    dominant_source=dp["dominant_source"],
                    store_frequency_per_week=vel,
                    recency_days=round(dp["recency_days"], 1),
                )
            )

        # ── Archetype ────────────────────────────────────────────────
        archetype, arch_confidence = _classify_archetype(pattern)
        completeness = _fingerprint_completeness(total, len(domain_prefs))

        return CognitiveFingerprint(
            tenant_id="default",
            project_filter=project,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            pattern=pattern,
            domain_preferences=domain_prefs,
            archetype=archetype,
            archetype_confidence=round(arch_confidence, 3),
            total_facts_analyzed=total,
            active_domains=len(domain_prefs),
            fingerprint_completeness=completeness,
        )


def _empty_fingerprint(project: Optional[str]) -> CognitiveFingerprint:
    """Return zeroed fingerprint when no facts exist."""
    return CognitiveFingerprint(
        tenant_id="default",
        project_filter=project,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        archetype="null_state",
        archetype_confidence=0.0,
        total_facts_analyzed=0,
        active_domains=0,
        fingerprint_completeness=0.0,
    )
