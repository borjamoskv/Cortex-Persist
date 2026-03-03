"""CORTEX v8+ — NREM Consolidation Cycle.

Unified orchestrator for the "sleep" sweep that transforms volatile
short-term memory into stable long-term knowledge.

Phases (modeled after NREM slow-wave sleep):
  1. Maturation  — Silent engrams that survived → promote to stable
  2. Pruning     — Depleted engrams (ATP < threshold) → destroy
  3. Synaptic decay — STDP edges decay globally (use-it-or-lose-it)
  4. Homeostatic scaling — Turrigiano normalization prevents runaway LTP/LTD

Each phase is independently skippable. The cycle returns a frozen
NREMReport with stats from every phase.

Derivation: Ω₂ (Entropic Asymmetry) + Ω₅ (Antifragile by Default)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Final

logger = logging.getLogger("cortex.memory.nrem_cycle")

__all__ = ["NREMConsolidationCycle", "NREMReport"]

# Maximum engrams to process in a single cycle to bound compute cost (Ω₂)
MAX_ENGRAMS_PER_CYCLE: Final[int] = 10_000


@dataclass(frozen=True, slots=True)
class NREMReport:
    """Immutable report from a single NREM consolidation cycle."""

    matured: int = 0
    deceased: int = 0
    pending: int = 0
    pruned: int = 0
    edges_decayed: int = 0
    edges_pruned: int = 0
    engrams_scaled: int = 0
    scaling_factor: float = 1.0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def total_mutations(self) -> int:
        """Total state changes applied during this cycle."""
        return (
            self.matured + self.deceased + self.pruned
            + self.edges_pruned + self.engrams_scaled
        )


class NREMConsolidationCycle:
    """Orchestrates the full NREM consolidation sweep.

    Wires together:
      - SystemsConsolidator (dual-trace maturation)
      - EntropyPruner (ATP-threshold pruning)
      - STDPEngine (synaptic decay)
      - HomeostaticScaler (Turrigiano normalization)

    All components are optional — the cycle degrades gracefully
    if any subsystem is unavailable.
    """

    __slots__ = (
        "_consolidator",
        "_pruner",
        "_stdp",
        "_scaler",
        "_decay_factor",
    )

    def __init__(
        self,
        consolidator: Any | None = None,
        pruner: Any | None = None,
        stdp_engine: Any | None = None,
        homeostatic_scaler: Any | None = None,
        decay_factor: float = 0.95,
    ) -> None:
        self._consolidator = consolidator
        self._pruner = pruner
        self._stdp = stdp_engine
        self._scaler = homeostatic_scaler
        self._decay_factor = decay_factor

    async def run(
        self,
        tenant_id: str,
        project_id: str | None = None,
    ) -> NREMReport:
        """Execute the full NREM consolidation cycle.

        Returns an immutable NREMReport with stats from all phases.
        """
        t0 = time.perf_counter()
        errors: list[str] = []

        # Phase 1: Maturation (silent → stable)
        matured = deceased = pending = 0
        if self._consolidator is not None:
            try:
                stats = await self._consolidator.consolidation_sweep(
                    tenant_id=tenant_id
                )
                matured = stats.get("matured", 0)
                deceased = stats.get("deceased", 0)
                pending = stats.get("pending", 0)
                logger.info(
                    "NREM Phase 1 (Maturation): matured=%d deceased=%d pending=%d",
                    matured, deceased, pending,
                )
            except (RuntimeError, ValueError, OSError) as exc:
                msg = f"Phase 1 (Maturation) failed: {exc}"
                logger.error(msg)
                errors.append(msg)

        # Phase 2: Entropy Pruning (depleted → destroyed)
        pruned = 0
        if self._pruner is not None:
            try:
                pruned = await self._pruner.prune_cycle(
                    tenant_id=tenant_id,
                    project_id=project_id,
                )
                logger.info("NREM Phase 2 (Pruning): pruned=%d", pruned)
            except (RuntimeError, ValueError, OSError) as exc:
                msg = f"Phase 2 (Pruning) failed: {exc}"
                logger.error(msg)
                errors.append(msg)

        # Phase 3: Synaptic Decay (STDP edge weakening)
        edges_decayed = edges_pruned = 0
        if self._stdp is not None:
            try:
                edges_pruned = self._stdp.decay_all(factor=self._decay_factor)
                edges_decayed = self._stdp.edge_count()
                logger.info(
                    "NREM Phase 3 (Synaptic Decay): edges_remaining=%d pruned=%d",
                    edges_decayed, edges_pruned,
                )
            except (RuntimeError, ValueError) as exc:
                msg = f"Phase 3 (Synaptic Decay) failed: {exc}"
                logger.error(msg)
                errors.append(msg)

        # Phase 4: Homeostatic Scaling (Turrigiano normalization)
        engrams_scaled = 0
        scaling_factor = 1.0
        if self._scaler is not None:
            try:
                result = await self._scaler.scale(
                    tenant_id=tenant_id,
                    project_id=project_id,
                )
                engrams_scaled = result.get("scaled", 0)
                scaling_factor = result.get("factor", 1.0)
                logger.info(
                    "NREM Phase 4 (Homeostatic Scaling): scaled=%d factor=%.4f",
                    engrams_scaled, scaling_factor,
                )
            except (RuntimeError, ValueError, OSError) as exc:
                msg = f"Phase 4 (Homeostatic Scaling) failed: {exc}"
                logger.error(msg)
                errors.append(msg)

        duration_ms = (time.perf_counter() - t0) * 1000.0

        report = NREMReport(
            matured=matured,
            deceased=deceased,
            pending=pending,
            pruned=pruned,
            edges_decayed=edges_decayed,
            edges_pruned=edges_pruned,
            engrams_scaled=engrams_scaled,
            scaling_factor=scaling_factor,
            duration_ms=round(duration_ms, 2),
            errors=errors,
        )

        logger.info(
            "NREM Cycle complete: mutations=%d duration=%.1fms errors=%d",
            report.total_mutations, report.duration_ms, len(errors),
        )
        return report
