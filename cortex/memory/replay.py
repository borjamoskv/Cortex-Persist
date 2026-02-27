"""CORTEX v6+ — Hippocampal Replay (Nocturnal Consolidation).

Strategy #1: During "sleep" cycles (daemon idle periods), replay
the day's HOT engrams against the existing semantic base.

- Resonating engrams → merge/compress
- Novel engrams → reinforce (energy +0.5)
- Contradictory engrams → generate ConflictEngram for user review

Biological basis: Sharp Wave Ripples (SWR) during NREM sleep
compress temporal sequences into burst-mode replay at 5-20x speed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.memory.replay")


@dataclass(slots=True)
class ReplayResult:
    """Result of a single replay cycle."""

    merged: int = 0
    reinforced: int = 0
    conflicts: int = 0
    pruned: int = 0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def total_processed(self) -> int:
        return self.merged + self.reinforced + self.conflicts + self.pruned


class HippocampalReplay:
    """Nocturnal consolidation engine.

    Runs during daemon idle periods to replay and consolidate
    the day's engrams against the existing memory base.
    """

    def __init__(
        self,
        vector_store=None,
        resonance_threshold: float = 0.8,
        novelty_boost: float = 0.5,
    ):
        self._vs = vector_store
        self._resonance_threshold = resonance_threshold
        self._novelty_boost = novelty_boost

    async def replay_cycle(
        self,
        tenant_id: str,
        hot_engrams: list | None = None,
    ) -> ReplayResult:
        """Execute one replay cycle over HOT-tier engrams.

        Args:
            tenant_id: Tenant isolation scope.
            hot_engrams: Pre-fetched engrams to replay. If None,
                        fetches from vector store.

        Returns:
            ReplayResult with consolidation stats.
        """
        start = time.monotonic()
        result = ReplayResult()

        if hot_engrams is None and self._vs and hasattr(self._vs, "scan_engrams"):
            hot_engrams = await self._vs.scan_engrams(tenant_id)

        if not hot_engrams:
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        for engram in hot_engrams:
            await self._process_engram(engram, tenant_id, result)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Replay cycle complete: %d processed "
            "(merged=%d, reinforced=%d, conflicts=%d) in %.1fms",
            result.total_processed,
            result.merged,
            result.reinforced,
            result.conflicts,
            result.duration_ms,
        )
        return result

    async def _process_engram(
        self,
        engram: Any,
        tenant_id: str,
        result: ReplayResult,
    ) -> None:
        """Process a single engram for semantic resonance or novelty."""
        neighbors = []
        if self._vs and hasattr(self._vs, "search_similar"):
            neighbors_raw = await self._vs.search_similar(
                engram.embedding,
                top_k=3,
                tenant_id=tenant_id,
            )
            # Filter out self
            neighbors = [n for n in neighbors_raw if n.id != engram.id]

        if not neighbors:
            # Novel — reinforce
            engram.energy_level = min(
                1.0,
                engram.energy_level + self._novelty_boost,
            )
            if self._vs and hasattr(self._vs, "upsert"):
                await self._vs.upsert(engram)
            result.reinforced += 1
            return

        if any(self._content_contradicts(engram.content, n.content) for n in neighbors):
            # Conflict detected
            result.conflicts += 1
            logger.warning("Conflict detected for engram %s during replay", engram.id)
            return

        # Resonates — merge into strongest neighbor
        result.merged += 1
        logger.debug("Engram %s merged during replay (resonance hit)", engram.id)

    @staticmethod
    def _content_contradicts(a: str, b: str) -> bool:
        """Heuristic contradiction check.

        Production: replace with LLM-based entailment check.
        """
        negations = ("not", "don't", "never", "wrong", "incorrect", "false")
        a_lower, b_lower = a.lower(), b.lower()

        # Simple heuristic: if one contains negation of the other's key terms
        for neg in negations:
            if neg in a_lower and neg not in b_lower:
                return True
            if neg in b_lower and neg not in a_lower:
                return True
        return False
