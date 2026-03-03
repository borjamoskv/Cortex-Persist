"""
F5 — CONFIDENCE THRESHOLD: AX-013: The Calibration Gap (Ω₃).
"""

from __future__ import annotations

from typing import Any

from cortex.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class ConfidenceFilter(ImmuneFilter):
    """F5: Confidence Threshold.
    
    Checks if the signal certainty is sufficient given the risk (R-level).
    """

    @property
    def filter_id(self) -> str:
        return "F5"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Analyze if confidence level matches risks."""
        
        # Confidence Level (C1-C5)
        # 1- Hypothesis, 2- Speculative, 3- Inferred, 4- Probable, 5- Confirmed
        confidence = context.get("confidence_level", 3)
        reversibility = context.get("reversibility_level", 1)  # R-level from context
        
        # Rule matrix (simplified)
        # R0: C1+
        # R1: C3+
        # R2: C3+ (with HOLD for lower)
        # R3: C5 only (otherwise HOLD/BLOCK)
        # R4: C5 only + Override
        
        verdict = Verdict.PASS
        justification = f"C{confidence} is sufficient for R{reversibility}."
        
        if reversibility >= 3:
            if confidence < 5:
                verdict = Verdict.HOLD
                justification = f"Semi-irreversible (R{reversibility}) requires C5 confirmation."
        elif reversibility >= 2:
            if confidence < 4:
                verdict = Verdict.HOLD
                justification = f"R2 action requires C4 probability level."
        elif reversibility >= 1:
            if confidence < 3:
                verdict = Verdict.HOLD
                justification = f"R1 action requires C3 inferred level."
        
        if confidence <= 1:
            verdict = Verdict.BLOCK
            justification = f"C1 hypothesis is insufficient for execution. Upgrade to C3+."
                
        return FilterResult(
            filter_id=self.filter_id,
            verdict=verdict,
            score=confidence * 20.0,
            justification=justification,
            metadata={"confidence": confidence, "reversibility": reversibility}
        )
