"""CORTEX v6+ — Thermodynamic Homeostasis Engine.

Implements active biological memory management (Forget Gates & Synaptic Pruning).
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.memory.engrams import CortexSemanticEngram

logger = logging.getLogger("cortex.memory.homeostasis")


class EntropyPruner:
    """Scans and regulates the structural entropy of the memory database.

    Simulates ATP-constrained synaptic pruning: if an Engram's predictive
    value (energy_level) falls below the threshold, it is actively destroyed
    to prevent semantic noise.
    """

    def __init__(self, vector_store: Any, atp_threshold: float = 0.2):
        self._vs = vector_store
        self._atp_threshold = atp_threshold

    async def prune_cycle(self, tenant_id: str, project_id: str | None = None) -> int:
        """Execute a circadian pruning cycle on the Vector Store.

        Returns the number of pruned engrams.
        """
        logger.info("Starting thermodynamic pruning cycle for tenant=%s", tenant_id)
        pruned_count = 0

        try:
            if not hasattr(self._vs, "scan_engrams"):
                return 0

            engrams = await self._vs.scan_engrams(tenant_id, project_id)
            for engram in engrams:
                if await self._prune_engram(engram):
                    pruned_count += 1

        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Pruning cycle failed: %s", e)

        return pruned_count

    async def _prune_engram(self, engram: Any) -> bool:
        """Evaluate and prune/update a single engram. Returns True if pruned."""
        if not isinstance(engram, CortexSemanticEngram):
            return False

        current_energy = engram.compute_decay()

        if current_energy < self._atp_threshold and not engram.is_diamond:
            logger.debug("Pruning depleted engram %s (E=%.2f)", engram.id, current_energy)
            await self._vs.delete(engram.id)
            return True

        if abs(current_energy - engram.energy_level) > 0.05:
            updated = engram.model_copy(update={"energy_level": current_energy})
            await self._vs.upsert(updated)

        return False


class DynamicSynapseUpdate:
    """Handles biological learning loops: strengthening existing links instead of copying."""

    def __init__(self, vector_store: Any):
        self._vs = vector_store

    async def reinforce(self, engram_id: str, boost: float = 0.2) -> bool:
        """Strengthen an existing engram to simulated Long-Term Potentiation."""
        try:
            if not hasattr(self._vs, "get_fact"):
                return False

            fact = await self._vs.get_fact(engram_id)
            if not isinstance(fact, CortexSemanticEngram):
                return False

            # Bypass frozen restrictions via immutable copying
            # to maintain semantic state
            updated = fact.model_copy(
                update={
                    "last_accessed": __import__("time").time(),
                    "energy_level": min(1.0, fact.energy_level + boost),
                }
            )
            await self._vs.upsert(updated)
            return True
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("Dynamic reinforcement failed for %s: %s", engram_id, e)

        return False
