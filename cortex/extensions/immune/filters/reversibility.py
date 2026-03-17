"""
F1 — REVERSIBILITY ANALYZER: AX-011: The Blast Radius (Ω₂).
"""

from __future__ import annotations

import enum
from typing import Any

from cortex.extensions.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class ReversibilityLevel(enum.IntEnum):
    R0 = 0  # Read-only
    R1 = 1  # Reversible with overhead (git commit/branch)
    R2 = 2  # Reversible with loss (file modification)
    R3 = 3  # Semi-irreversible (git push, extern call)
    R4 = 4  # Irreversible (deploy, delete)


class ReversibilityFilter(ImmuneFilter):
    """F1: Reversibility Analyzer.

    Checks if an action can be undone and calculates the potential blast radius.
    """

    @property
    def filter_id(self) -> str:
        return "F1"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Evaluate reversibility of the proposed intent/signal."""
        # Simple R-level mapping for demonstration
        # In a real scenario, we'd parse the intent details (files affected, command type)
        level: ReversibilityLevel = context.get("reversibility_level", ReversibilityLevel.R1)

        # Blast radius calculation (heuristic)
        # blast_radius = (archivos_afectados × 10) + (dependencias_downstream × 20) + (irreversibilidad × 50)
        arch_count = len(context.get("affected_paths", []))
        deps_count = context.get("downstream_dependencies_count", 0)

        blast_radius = (arch_count * 10) + (deps_count * 20) + (level.value * 50)

        verdict = Verdict.PASS
        justification = f"Reversibility level {level.name} (Blast radius: {blast_radius})."
        score = max(0, 100 - blast_radius / 2.0)

        if level == ReversibilityLevel.R4:
            verdict = Verdict.BLOCK
            justification = "Irreversible action (R4) rejected by policy. Requires immune-override."
        elif level == ReversibilityLevel.R3:
            verdict = Verdict.HOLD
            justification = "Semi-irreversible action (R3) requires explicit confirmation."
        elif blast_radius > 100:
            verdict = Verdict.HOLD
            justification = f"Blast radius too high ({blast_radius}). Requires manual review."

        return FilterResult(
            filter_id=self.filter_id,
            verdict=verdict,
            score=score,
            justification=justification,
            metadata={"reversibility_level": level.name, "blast_radius": blast_radius},
        )
