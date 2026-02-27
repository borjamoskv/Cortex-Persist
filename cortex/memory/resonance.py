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
from typing import Any

from cortex.memory.engrams import CortexSemanticEngram

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
    """ART-inspired gate that controls memory write operations.

    The vigilance parameter ρ (rho) determines the threshold for
    pattern matching. Higher ρ = more granular memory (more categories).
    Lower ρ = more generalization (fewer, broader engrams).

    Biological analogy:
    - ρ = parameter of vigilance (Grossberg's F1 comparison field)
    - Resonance = match → reinforce existing engram (LTP)
    - Reset = mismatch → create new engram category
    """

    def __init__(
        self,
        vector_store: Any,
        rho: float = 0.85,
        ltp_boost: float = 0.25,
    ):
        self._vs = vector_store
        self._rho = rho
        self._ltp_boost = ltp_boost

    async def gate(
        self,
        candidate: CortexSemanticEngram,
        search_limit: int = 10,
    ) -> tuple[str, CortexSemanticEngram]:
        """Evaluate a candidate engram against existing memory.

        Returns:
            ("resonance", existing_engram) if match found and reinforced.
            ("reset", candidate) if new engram was inserted.
        """
        import time as _time

        # Search for nearest neighbors in vector store
        if hasattr(self._vs, "search_similar"):
            neighbors = await self._vs.search_similar(
                embedding=candidate.embedding,
                tenant_id=candidate.tenant_id,
                limit=search_limit,
            )
        else:
            logger.debug("Vector store lacks search_similar; falling through to RESET.")
            neighbors = []

        # Check for resonance (match above vigilance threshold)
        best_match: CortexSemanticEngram | None = None
        best_sim = 0.0

        for neighbor in neighbors:
            if not isinstance(neighbor, CortexSemanticEngram):
                continue
            sim = cosine_similarity(candidate.embedding, neighbor.embedding)
            if sim > best_sim:
                best_sim = sim
                best_match = neighbor

        if best_match is not None and best_sim >= self._rho:
            # RESONANCE → Reinforce existing engram via LTP
            reinforced = best_match.model_copy(
                update={
                    "last_accessed": _time.time(),
                    "energy_level": min(
                        1.0,
                        best_match.energy_level + self._ltp_boost,
                    ),
                    # Merge entangled refs (connectomics)
                    "entangled_refs": list(set(best_match.entangled_refs) | {candidate.id}),
                }
            )
            if hasattr(self._vs, "upsert"):
                await self._vs.upsert(reinforced)
            logger.info(
                "ART RESONANCE: engram %s reinforced (sim=%.3f, E=%.2f→%.2f)",
                best_match.id,
                best_sim,
                best_match.energy_level,
                reinforced.energy_level,
            )
            return ("resonance", reinforced)

        # RESET → Insert new engram category
        if hasattr(self._vs, "upsert"):
            await self._vs.upsert(candidate)
        logger.info(
            "ART RESET: new engram %s created (best_sim=%.3f < ρ=%.2f)",
            candidate.id,
            best_sim,
            self._rho,
        )
        return ("reset", candidate)
