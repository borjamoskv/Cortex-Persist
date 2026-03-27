"""
F4 — EXERGY MEASURE: AX-012: The Threshold of Thermodynamics (Ω₂).
"""

from __future__ import annotations

from typing import Any

from cortex.extensions.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class ExergyFilter(ImmuneFilter):
    """F4: Exergy Measure.

    Checks if an action provides net positive exergy (complexity reduction).
    AX-012: Every abstraction has real thermodynamic cost.
    """

    @property
    def filter_id(self) -> str:
        return "F4"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Measure exergy change (ΔE) pre-execution."""

        # exergy_delta = complexity_removed - complexity_added
        comp_added = context.get("complexity_added", 0.0)
        comp_removed = context.get("complexity_removed", 0.0)

        # 1 abstraction = 3.0, 1 dependency = 5.0, 1 LOC = 0.1, 1 file = 2.0
        exergy_delta = comp_removed - comp_added

        verdict = Verdict.PASS
        justification = f"Exergy delta: {exergy_delta:.2f} (Net-Positive Exergy policy: Ω₂)."

        if exergy_delta < -10.0:
            verdict = Verdict.BLOCK
            justification = (
                f"Action destroys too much exergy ({exergy_delta:.2f}). Rejected by Axiom Ω₂."
            )
        elif exergy_delta < 0.0:
            verdict = Verdict.HOLD
            justification = (
                f"Net exergy negative ({exergy_delta:.2f}). Justify why complexity is necessary."
            )
        elif exergy_delta > 5.0:
            # Bonus pass for high exergy gain
            justification = f"Major exergy gain ({exergy_delta:.2f}). Bonus Pass (Ω₇)."

        return FilterResult(
            filter_id=self.filter_id,
            verdict=verdict,
            score=min(100, max(0, 50 + exergy_delta * 5.0)),
            justification=justification,
            metadata={"delta": exergy_delta, "is_net_positive": exergy_delta >= 0.0},
        )
