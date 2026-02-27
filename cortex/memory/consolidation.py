"""CORTEX v6+ — Silent Engrams & Systems Consolidation.

Strategy 4: Implements Tonegawa's discovery of silent engrams.

When a fact is stored, TWO engrams are created simultaneously:
  - Active engram in L2-hot (hippocampus): immediately searchable.
  - Silent engram in L3 (cortex): invisible to search until matured.

The silent engram matures autonomously over N days without contradiction.
If the active engram decays but the silent one has matured → memory persists.
If both decay → natural death (thermodynamic pruning).

Compute-in-Memory principle: Each engram carries its OWN maturation logic
as embedded methods, not as external daemon processing. The memory IS
the processor — no separation between storage and computation.
"""

from __future__ import annotations

import enum
import logging
import time

from pydantic import Field

from cortex.memory.engrams import CortexSemanticEngram

logger = logging.getLogger("cortex.memory.consolidation")


class EngramState(str, enum.Enum):
    """Lifecycle state of an engram in the consolidation pipeline."""

    ACTIVE = "active"  # Hippocampal — immediately retrievable
    SILENT = "silent"  # Cortical — exists but invisible to search
    MATURED = "matured"  # Cortical — fully consolidated, stable
    DECEASED = "deceased"  # Pruned — marked for garbage collection


# Maturation period in days before a silent engram becomes visible
DEFAULT_MATURATION_DAYS = 3.0

# Minimum energy the active twin must maintain to keep the silent alive
ACTIVE_TWIN_MIN_ENERGY = 0.15


class SilentEngram(CortexSemanticEngram):
    """An engram that exists but is invisible to regular search.

    Implements compute-in-memory: the engram carries its own maturation
    logic. No external daemon needed to decide if it matures — the
    engram IS the processor of its own lifecycle.

    Biological analogy:
      - Created simultaneously with active twin in hippocampus
      - Resides in prefrontal cortex, initially silent
      - Cannot be recalled by natural cues, only by direct stimulation
      - Matures over days/weeks as hippocampal trace weakens
    """

    state: EngramState = Field(
        default=EngramState.SILENT,
        description="Current lifecycle state.",
    )
    active_twin_id: str = Field(
        default="",
        description="UUID of the active hippocampal twin.",
    )
    created_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp of creation.",
    )
    maturation_days: float = Field(
        default=DEFAULT_MATURATION_DAYS,
        description="Days required to mature from silent to active.",
    )
    contradiction_count: int = Field(
        default=0,
        description="Number of contradictory signals received.",
    )

    # ─── Compute-in-Memory: Self-contained lifecycle logic ───────

    def age_days(self) -> float:
        """How old is this engram in days."""
        return max(0.0, (time.time() - self.created_at) / 86400.0)

    def is_mature(self) -> bool:
        """Check if this silent engram has completed maturation.

        Maturation requires:
        1. Sufficient time has passed (≥ maturation_days)
        2. No contradictions received during maturation
        3. Energy level hasn't collapsed
        """
        if self.state == EngramState.MATURED:
            return True
        if self.state == EngramState.DECEASED:
            return False

        age = self.age_days()
        has_aged = age >= self.maturation_days
        is_clean = self.contradiction_count == 0
        has_energy = self.compute_decay() > 0.1

        return has_aged and is_clean and has_energy

    def tick(self) -> EngramState:
        """Self-evaluate lifecycle state. Compute-in-memory.

        The engram decides its OWN fate — no external orchestrator.
        Returns the new state after evaluation.
        """
        if self.state == EngramState.DECEASED:
            return EngramState.DECEASED

        # Check for death conditions
        current_energy = self.compute_decay()
        if current_energy <= 0.0 and self.contradiction_count > 0:
            return EngramState.DECEASED

        # Check for maturation
        if self.state == EngramState.SILENT and self.is_mature():
            return EngramState.MATURED

        return self.state

    def contradict(self) -> None:
        """Register a contradictory signal. Delays maturation."""
        object.__setattr__(
            self,
            "contradiction_count",
            self.contradiction_count + 1,
        )
        # Each contradiction resets the maturation clock
        object.__setattr__(self, "created_at", time.time())
        logger.debug(
            "Engram %s received contradiction #%d, maturation clock reset.",
            self.id,
            self.contradiction_count,
        )


class SystemsConsolidator:
    """Orchestrates the dual-trace memory consolidation pipeline.

    When a new fact arrives:
    1. Creates an ACTIVE engram (L2-hot, hippocampus)
    2. Creates a SILENT twin (L3, prefrontal cortex)
    3. Over time, the active trace weakens naturally
    4. The silent trace matures if no contradictions arrive
    5. Once matured, the silent engram becomes searchable

    This mimics the hippocampal-cortical transfer observed in
    Tonegawa's optogenetic engram experiments.
    """

    def __init__(self, vector_store, maturation_days: float = 3.0):
        self._vs = vector_store
        self._maturation_days = maturation_days

    async def dual_store(
        self,
        engram: CortexSemanticEngram,
    ) -> tuple[CortexSemanticEngram, SilentEngram]:
        """Create dual-trace memory: active + silent engram pair.

        Returns (active_engram, silent_engram).
        """
        import uuid

        # 1. Store the active engram (hippocampal trace)
        if hasattr(self._vs, "upsert"):
            await self._vs.upsert(engram)

        # 2. Create and store the silent twin (cortical trace)
        silent = SilentEngram(
            id=str(uuid.uuid4()),
            tenant_id=engram.tenant_id,
            project_id=engram.project_id,
            content=engram.content,
            embedding=engram.embedding,
            energy_level=0.5,  # Starts weaker than active
            entangled_refs=[engram.id],
            state=EngramState.SILENT,
            active_twin_id=engram.id,
            maturation_days=self._maturation_days,
            is_diamond=engram.is_diamond,
            is_bridge=engram.is_bridge,
            confidence=engram.confidence,
            metadata={
                **engram.metadata,
                "consolidation": "silent_twin",
            },
        )

        if hasattr(self._vs, "upsert"):
            await self._vs.upsert(silent)

        logger.info(
            "Dual-trace created: active=%s, silent=%s (maturation in %.1f days)",
            engram.id,
            silent.id,
            self._maturation_days,
        )

        return (engram, silent)

    async def consolidation_sweep(
        self,
        tenant_id: str,
    ) -> dict[str, int]:
        """Run a consolidation sweep: mature or prune silent engrams.

        Returns stats: {"matured": N, "deceased": N, "pending": N}.
        """
        stats = {"matured": 0, "deceased": 0, "pending": 0}

        if not hasattr(self._vs, "scan_engrams"):
            return stats

        engrams = await self._vs.scan_engrams(tenant_id)

        for engram in engrams:
            if not isinstance(engram, SilentEngram):
                continue

            new_state = engram.tick()

            if new_state == EngramState.MATURED and engram.state != EngramState.MATURED:
                # Promote to searchable
                matured = engram.model_copy(update={"state": EngramState.MATURED})
                await self._vs.upsert(matured)
                stats["matured"] += 1
                logger.info(
                    "Silent engram %s MATURED after %.1f days.",
                    engram.id,
                    engram.age_days(),
                )

            elif new_state == EngramState.DECEASED:
                await self._vs.delete(engram.id)
                stats["deceased"] += 1
                logger.info(
                    "Silent engram %s DECEASED (contradictions=%d).",
                    engram.id,
                    engram.contradiction_count,
                )

            else:
                stats["pending"] += 1

        return stats
