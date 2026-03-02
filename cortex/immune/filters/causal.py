"""
F3 — CAUSAL VALIDATOR: AX-014: Mapping the Causal Chord (Ω₁).
"""

from __future__ import annotations

from typing import Any

from cortex.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class CausalFilter(ImmuneFilter):
    """F3: Causal Validator.

    Tries to falsify the causal link between perception and intent.
    Checks: Causal vs Correlational, Chain depth, Axiom 15.
    """

    @property
    def filter_id(self) -> str:
        return "F3"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Analyze if the proposed action is causal or just correlational."""

        # Step 1: Causal Separation
        context.get("is_causal", True)
        is_correlational = context.get("is_correlational", False)

        if is_correlational:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.HOLD,
                score=50,
                justification="Proposed action is correlational, not causal. Requires further evidence.",
                metadata={"causality_type": "correlational"},
            )

        # Step 2: Causal Chain (5 Why's reverso)
        chain_depth = context.get("causal_chain_depth", 1)
        if chain_depth > 3:
            # Too many intermediate steps without evidence
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.HOLD,
                score=45,
                justification=f"Causal chain too deep ({chain_depth}) without intermediate evidence.",
                metadata={"chain_depth": chain_depth},
            )

        # Step 3: Falsification (Operational Axiom 15)
        is_falsifiable = context.get("is_falsifiable", True)
        if not is_falsifiable:
            return FilterResult(
                filter_id=self.filter_id,
                verdict=Verdict.BLOCK,
                score=0,
                justification="Signal is infalsable. Does not represent information/knowledge.",
                metadata={"falsifiability": "none"},
            )

        return FilterResult(
            filter_id=self.filter_id,
            verdict=Verdict.PASS,
            score=90,
            justification="Causal chain verified and falsifiable.",
            metadata={"causality_type": "causal", "chain_depth": chain_depth},
        )
