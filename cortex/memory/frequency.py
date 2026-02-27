"""CORTEX v6+ — Continuous Memory System (CMS) & BIFT Frequency Bands.

Strategy 1 (CMS): Stratifies memory into frequency layers with different
update cadences, inspired by HOPE/Titans Nested Learning.

Strategy 5 (BIFT): Maps retrieval to oscillatory frequency bands
inspired by neural oscillations (gamma, beta, theta, delta).

Together they create a hierarchical temporal memory where engrams
ascend in frequency if they persist and decay if ephemeral.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.memory.frequency")


# ─── Strategy 1: Continuous Memory System (CMS) ─────────────────────


class MemoryFrequency(str, enum.Enum):
    """Memory tier frequencies inspired by HOPE/Titans."""

    HOT = "hot"  # Every query — working memory
    WARM = "warm"  # Every 16-64 interactions — semantic patterns
    COLD = "cold"  # Every 256+ interactions — architectural decisions
    PERMAFROST = "permafrost"  # Once per project — foundational axioms


# Interaction thresholds for promotion between tiers
PROMOTION_THRESHOLDS: dict[MemoryFrequency, int] = {
    MemoryFrequency.HOT: 0,  # Default entry
    MemoryFrequency.WARM: 8,  # 8+ accesses → warm
    MemoryFrequency.COLD: 32,  # 32+ accesses → cold (stable)
    MemoryFrequency.PERMAFROST: 128,  # 128+ accesses → axiom
}

# Energy thresholds for demotion (decay)
DEMOTION_ENERGY: dict[MemoryFrequency, float] = {
    MemoryFrequency.HOT: 0.0,
    MemoryFrequency.WARM: 0.3,
    MemoryFrequency.COLD: 0.5,
    MemoryFrequency.PERMAFROST: 0.8,
}


@dataclass(slots=True)
class FrequencyMetadata:
    """Metadata tracking an engram's frequency tier and access count."""

    tier: MemoryFrequency = MemoryFrequency.HOT
    access_count: int = 0
    promotion_history: list[str] | None = None


class ContinuousMemorySystem:
    """Manages frequency-based memory stratification.

    Engrams enter at HOT and promote to higher stability tiers
    based on access frequency. They demote (or get pruned) if
    their energy drops below the tier's minimum threshold.
    """

    def __init__(self, vector_store: Any):
        self._vs = vector_store

    def classify_tier(
        self,
        access_count: int,
        energy_level: float,
    ) -> MemoryFrequency:
        """Determine the appropriate tier for an engram."""
        # Check from most stable to least stable
        for tier in reversed(list(MemoryFrequency)):
            threshold = PROMOTION_THRESHOLDS[tier]
            min_energy = DEMOTION_ENERGY[tier]
            if access_count >= threshold and energy_level >= min_energy:
                return tier
        return MemoryFrequency.HOT

    def evaluate_and_migrate(
        self,
        engram_id: str,
        current_access_count: int,
        current_energy: float,
        current_tier: MemoryFrequency,
    ) -> MemoryFrequency:
        """Evaluate if an engram should be promoted or demoted.

        Returns the new tier (may be same as current).
        """
        new_tier = self.classify_tier(current_access_count, current_energy)

        if new_tier != current_tier:
            direction = "PROMOTED" if new_tier.value > current_tier.value else "DEMOTED"
            logger.info(
                "CMS %s: engram %s %s→%s (accesses=%d, E=%.2f)",
                direction,
                engram_id,
                current_tier.value,
                new_tier.value,
                current_access_count,
                current_energy,
            )

        return new_tier


# ─── Strategy 5: BIFT Frequency Bands for Retrieval ─────────────────


class RetrievalBand(str, enum.Enum):
    """Neural oscillation-inspired retrieval bands."""

    GAMMA = "gamma"  # High freq: exact match, keyword, recent facts
    BETA = "beta"  # Standard: cosine similarity semantic search
    THETA = "theta"  # Low freq: cross-project bridges, long-range
    DELTA = "delta"  # Lowest: axioms, immutable rules, diamonds


# Band configuration: maps to search parameters
@dataclass(slots=True, frozen=True)
class BandConfig:
    """Configuration for a retrieval frequency band."""

    max_results: int
    min_energy: float
    require_diamond: bool
    cross_project: bool


BAND_CONFIGS: dict[RetrievalBand, BandConfig] = {
    RetrievalBand.GAMMA: BandConfig(
        max_results=5,
        min_energy=0.6,
        require_diamond=False,
        cross_project=False,
    ),
    RetrievalBand.BETA: BandConfig(
        max_results=10,
        min_energy=0.3,
        require_diamond=False,
        cross_project=False,
    ),
    RetrievalBand.THETA: BandConfig(
        max_results=15,
        min_energy=0.1,
        require_diamond=False,
        cross_project=True,
    ),
    RetrievalBand.DELTA: BandConfig(
        max_results=20,
        min_energy=0.0,
        require_diamond=True,
        cross_project=True,
    ),
}


class BIFTRouter:
    """Routes retrieval queries to the appropriate frequency band.

    Inspired by brain oscillations where gamma handles local attention
    and theta/delta handle long-range integration.
    """

    @staticmethod
    def classify_query(
        query: str,
        is_cross_project: bool = False,
        is_axiom_lookup: bool = False,
    ) -> RetrievalBand:
        """Classify a query into its optimal frequency band."""
        if is_axiom_lookup:
            return RetrievalBand.DELTA
        if is_cross_project:
            return RetrievalBand.THETA

        # Heuristic: short queries with exact keywords → gamma
        words = query.split()
        if len(words) <= 3:
            return RetrievalBand.GAMMA

        # Default → standard semantic search
        return RetrievalBand.BETA

    @staticmethod
    def get_config(band: RetrievalBand) -> BandConfig:
        """Get the search configuration for a band."""
        return BAND_CONFIGS[band]
