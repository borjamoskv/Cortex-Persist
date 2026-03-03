"""CORTEX v6+ — Adaptive Resonance Gate (ART-inspired).

Implements Grossberg's Adaptive Resonance Theory as a pre-store filter.
Instead of blindly appending facts, the gate checks for semantic resonance
with existing engrams. If resonance is found (similarity > ρ), LTP is applied.
If not, a new engram is created.

Strategy 2: Eliminates semantic duplication at the source.
"""

from __future__ import annotations

import logging
import math
from typing import Any, TYPE_CHECKING

from cortex.memory.engrams import CortexSemanticEngram

if TYPE_CHECKING:
    from cortex.sovereign.endocrine import DigitalEndocrine

logger = logging.getLogger("cortex.memory.resonance")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


class AdaptiveResonanceGate:
    """ART-v2 inspired gate that controls memory write operations.

    The vigilance parameter ρ (rho) determines the threshold for
    pattern matching.

    Enhancements for v6.1:
    - Dynamic Rho: Adjusts vigilance based on context (Precision vs Recall modes).
    - Topographic Boost: Resonates with physical "ghosts" in the filesystem field.
    - Metabolic Filtering: Incorporates engram energy levels into resonance probability.
    """

    def __init__(
        self,
        vector_store: Any,
        rho: float = 0.85,
        ltp_boost: float = 0.25,
        songline_sensor: Any | None = None,
        endocrine: DigitalEndocrine | None = None,
    ):
        self._vs = vector_store
        self._rho = rho
        self._ltp_boost = ltp_boost
        self._sensor = songline_sensor
        self._endocrine = endocrine

    def _calculate_topographic_boost(
        self, candidate: CortexSemanticEngram
    ) -> float:
        """Evaluate if the candidate resonates with any physical 'ghosts' in its field."""
        if not self._sensor or not hasattr(candidate, "source_file"):
            return 0.0

        # Optional: scan field around the source file
        try:
            from pathlib import Path
            field = self._sensor.scan_field(Path(candidate.source_file).parent)
            # Find ghosts matching intent or project
            for ghost in field:
                if ghost.get("project") == candidate.project:
                    # Found a physical trace of the same project context
                    return 0.05  # Static boost for topographic proximity
        except (OSError, AttributeError, TypeError) as exc:
            logger.debug(
                "Topographic boost unavailable for engram %s: %s",
                getattr(candidate, "id", "?"),
                exc,
            )

        return 0.0

    def _calculate_endocrine_shift(self) -> float:
        """Modulate vigilance based on biological system state.
        
        Cortisol (Stress) -> Increases rho (Stricter matching, defensive)
        Dopamine (Creativity) -> Decreases rho (Broader resonance, exploratory)
        """
        if not self._endocrine:
            return 0.0
        shift = (self._endocrine.cortisol * 0.1) - (self._endocrine.dopamine * 0.05)
        return float(shift)

    async def _find_neighbors(self, candidate: CortexSemanticEngram, limit: int) -> list[Any]:
        """Search for nearest neighbors in vector store."""
        if hasattr(self._vs, "search_similar"):
            return await self._vs.search_similar(
                embedding=candidate.embedding,
                tenant_id=candidate.tenant_id,
                limit=limit,
            )
        logger.debug("Vector store lacks search_similar; falling through.")
        return []

    def _evaluate_resonance(
        self,
        candidate: CortexSemanticEngram,
        neighbors: list[Any],
        rho: float,
        topo_boost: float,
    ) -> tuple[CortexSemanticEngram | None, float]:
        """Find the best matching engram above vigilance threshold."""
        best_match: CortexSemanticEngram | None = None
        best_sim = 0.0

        for neighbor in neighbors:
            if not isinstance(neighbor, CortexSemanticEngram):
                continue

            # Semantic Similarity
            sim = cosine_similarity(candidate.embedding, neighbor.embedding)

            # Metabolic Modifier: Lower energy engrams are harder to "wake up"
            current_energy = neighbor.compute_decay()
            metabolic_penalty = (1.0 - current_energy) * 0.05

            effective_sim = sim + topo_boost - metabolic_penalty

            if effective_sim > best_sim:
                best_sim = effective_sim
                best_match = neighbor

        return (best_match if best_sim >= rho else None), best_sim

    async def gate(
        self,
        candidate: CortexSemanticEngram,
        search_limit: int = 15,
        vigilance_override: float | None = None,
        precision_mode: bool = False,
    ) -> tuple[str, CortexSemanticEngram]:
        """Evaluate a candidate engram against existing memory with adaptive vigilance.

        Returns:
            ("resonance", existing_engram) if match found and reinforced.
            ("reset", candidate) if new engram was inserted.
        """
        import time as _time

        # 1. Dynamic Vigilance Adjustment
        rho = vigilance_override or self._rho

        # Endocrine Modulation [v6.2]
        endocrine_shift = self._calculate_endocrine_shift()
        rho = max(0.5, min(0.98, rho + endocrine_shift))

        if precision_mode:
            rho = min(0.98, rho + 0.1)

        # 2. Find Neighbors and Topology Boost
        neighbors = await self._find_neighbors(candidate, search_limit)
        topo_boost = self._calculate_topographic_boost(candidate)

        # 3. Evaluate Resonance
        best_match, best_sim = self._evaluate_resonance(
            candidate, neighbors, rho, topo_boost
        )

        if best_match:
            # RESONANCE → Reinforce (LTP)
            boost = self._ltp_boost + (0.05 if precision_mode else 0.0)
            reinforced = best_match.model_copy(
                update={
                    "last_accessed": _time.time(),
                    "energy_level": min(1.0, best_match.energy_level + boost),
                    "entangled_refs": list(set(best_match.entangled_refs) | {candidate.id}),
                }
            )

            if hasattr(self._vs, "upsert"):
                await self._vs.upsert(reinforced)

            logger.info(
                "ART RESONANCE [v6.1]: engram %s reinforced (sim=%.3f, boost=%.3f)",
                best_match.id,
                best_sim,
                topo_boost,
            )
            return ("resonance", reinforced)

        # RESET → Insert new engram category
        if hasattr(self._vs, "upsert"):
            await self._vs.upsert(candidate)

        logger.info(
            "ART RESET [v6.1]: new engram %s created (best_sim=%.3f < ρ=%.2f)",
            candidate.id,
            best_sim,
            rho,
        )
        return ("reset", candidate)
