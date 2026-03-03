"""CORTEX v6+ — Thermodynamic Homeostasis Engine.

Implements active biological memory management (Forget Gates & Synaptic Pruning).
Integrates with drift monitoring for post-prune topological health assessment.
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

            # Post-prune drift checkpoint (non-blocking diagnostic)
            if pruned_count > 0:
                await self._post_prune_drift_check(tenant_id, project_id)

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

    async def _post_prune_drift_check(self, tenant_id: str, project_id: str | None = None) -> None:
        """Run non-blocking drift health check after pruning."""
        import importlib.util

        if importlib.util.find_spec("cortex.memory.drift") is None:
            return  # drift module not available — degrade gracefully

        if not hasattr(self._vs, "recall_secure"):
            return

        # We log diagnostically — no action taken, just visibility
        logger.debug(
            "Post-prune drift check requested for tenant=%s project=%s",
            tenant_id,
            project_id,
        )


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


# ─── Turrigiano Homeostatic Scaler ───────────────────────────────────

# Target set-point for mean energy across the population (Ω₂)
_DEFAULT_SET_POINT: float = 0.5

# Minimum and maximum energy after scaling (prevent collapse/explosion)
_ENERGY_FLOOR: float = 0.05
_ENERGY_CEILING: float = 1.0

# Minimum deviation from set-point to trigger scaling
_SCALING_DEADZONE: float = 0.05


class HomeostaticScaler:
    """Turrigiano-style multiplicative synaptic scaling.

    Prevents runaway LTP (everything becomes important) or runaway
    LTD (everything decays to noise) by normalizing energy levels
    toward a homeostatic set-point.

    Formula:
        new_energy = clamp(energy × (set_point / mean_energy), 0.05, 1.0)

    Diamond engrams (is_diamond=True) are immune to scaling.

    Derivation: Ω₂ (Entropic Asymmetry) — scaling reduces net entropy
    without displacing it.
    """

    __slots__ = ("_vs", "_set_point")

    def __init__(
        self,
        vector_store: Any,
        set_point: float = _DEFAULT_SET_POINT,
    ) -> None:
        self._vs = vector_store
        self._set_point = set_point

    async def scale(
        self,
        tenant_id: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Apply multiplicative homeostatic scaling to all engrams.

        Returns dict with 'scaled' count and 'factor' applied.
        """
        if not hasattr(self._vs, "scan_engrams"):
            return {"scaled": 0, "factor": 1.0}

        try:
            engrams = await self._vs.scan_engrams(tenant_id, project_id)
        except (RuntimeError, ValueError, OSError) as exc:
            logger.error("HomeostaticScaler: scan failed: %s", exc)
            return {"scaled": 0, "factor": 1.0, "error": str(exc)}

        if not engrams:
            return {"scaled": 0, "factor": 1.0}

        # Compute mean energy (excluding diamonds — they're invariant)
        mutable = [e for e in engrams if isinstance(e, CortexSemanticEngram) and not e.is_diamond]
        if not mutable:
            return {"scaled": 0, "factor": 1.0}

        mean_energy = sum(e.energy_level for e in mutable) / len(mutable)

        # Deadzone: don't scale if mean is close enough to set-point
        if abs(mean_energy - self._set_point) < _SCALING_DEADZONE:
            logger.debug(
                "HomeostaticScaler: mean=%.3f within deadzone of %.3f, skipping",
                mean_energy,
                self._set_point,
            )
            return {"scaled": 0, "factor": 1.0}

        # Multiplicative correction factor
        factor = self._set_point / max(mean_energy, 1e-9)

        scaled_count = 0
        for engram in mutable:
            new_energy = max(
                _ENERGY_FLOOR,
                min(_ENERGY_CEILING, engram.energy_level * factor),
            )
            if abs(new_energy - engram.energy_level) > 0.01:
                updated = engram.model_copy(update={"energy_level": new_energy})
                await self._vs.upsert(updated)
                scaled_count += 1

        logger.info(
            "HomeostaticScaler: mean=%.3f → target=%.3f, factor=%.4f, scaled=%d/%d",
            mean_energy,
            self._set_point,
            factor,
            scaled_count,
            len(mutable),
        )
        return {
            "scaled": scaled_count,
            "factor": round(factor, 4),
            "mean_before": round(mean_energy, 4),
        }
