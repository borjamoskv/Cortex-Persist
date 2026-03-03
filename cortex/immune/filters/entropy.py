"""
F4 — ENTROPY MEASURE: AX-012: The Threshold of Thermodynamics (Ω₂).
"""

from __future__ import annotations

from typing import Any

from cortex.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class EntropyFilter(ImmuneFilter):
    """F4: Entropy Measure.

    Checks if an action adds more complexity than it removes.
    AX-012: Every abstraction has real thermodynamic cost.
    """

    @property
    def filter_id(self) -> str:
        return "F4"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Measure entropy change (H) pre-execution."""

        # entropy_delta = complexity_added - complexity_removed
        comp_added = context.get("complexity_added", 0.0)
        comp_removed = context.get("complexity_removed", 0.0)

        # 1 abstraction = 3.0, 1 dependency = 5.0, 1 LOC = 0.1, 1 file = 2.0
        # In a real scenario, we'd use Astor/AST or lines count

        entropy_delta = comp_added - comp_removed

        verdict = Verdict.PASS
        justification = f"Entropy delta: {entropy_delta:.2f} (Net-Negative Entropy policy: Ω₂)."

        if entropy_delta > 10.0:
            verdict = Verdict.BLOCK
            justification = (
                f"Action adds too much entropy ({entropy_delta:.2f}). Rejected by Axiom Ω₂."
            )
        elif entropy_delta > 0.0:
            verdict = Verdict.HOLD
            justification = (
                f"Net entropy positive ({entropy_delta:.2f}). Justify why complexity is necessary."
            )
        elif entropy_delta < -5.0:
            # Bonus pass for high entropy reduction
            justification = f"Major complexity reduction ({entropy_delta:.2f}). Bonus Pass (Ω₇)."

        return FilterResult(
            filter_id=self.filter_id,
            verdict=verdict,
            score=max(0, 100 - entropy_delta * 5.0),
            justification=justification,
            metadata={"delta": entropy_delta, "is_net_negative": entropy_delta <= 0.0},
        )
