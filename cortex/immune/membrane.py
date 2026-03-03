"""
Cortex Immune Membrane — The Sovereign Arbiter.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from cortex.immune.filters.adversarial import AdversarialFilter
from cortex.immune.filters.base import FilterResult, ImmuneFilter, Verdict
from cortex.immune.filters.causal import CausalFilter
from cortex.immune.filters.confidence import ConfidenceFilter
from cortex.immune.filters.entropy import EntropyFilter
from cortex.immune.filters.reversibility import ReversibilityFilter

logger = logging.getLogger("cortex.immune.membrane")


@dataclass(frozen=True, slots=True)
class TriageReport:
    """Consolidated result from the immune membrane triage."""

    verdict: Verdict
    triage_score: float
    filter_results: list[FilterResult]
    blast_radius: float
    immunity_certificate: bool
    risks_assumed: list[str]
    cortex_persistence: bool


class ImmuneMembrane:
    """A membrane with 5 layers that intercepts and validates signals."""

    def __init__(self):
        self._filters: list[ImmuneFilter] = [
            ReversibilityFilter(),
            AdversarialFilter(),
            CausalFilter(),
            EntropyFilter(),
            ConfidenceFilter(),
        ]

    async def intercept(self, intent: Any, context: dict[str, Any]) -> TriageReport:
        """Evaluate a proposed intent against all immunological filters in parallel."""
        logger.info(f"Intercepting intent: {intent}")

        # Parallel evaluation via asyncio.gather
        tasks = [f.evaluate(intent, context) for f in self._filters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        filter_results: list[FilterResult] = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Filter failure: {res}")
                # Failure counts as BLOCK to be safe
                filter_results.append(
                    FilterResult(
                        filter_id="IMMUNE_ERROR",
                        verdict=Verdict.BLOCK,
                        score=0,
                        justification=f"Filter internal error: {res}",
                    )
                )
            else:
                filter_results.append(res)

        return self._triage(filter_results)

    def _triage(self, results: list[FilterResult]) -> TriageReport:
        """Consolidate the results from the 5 filters."""

        # Rule 1: BLOCK in any filter = BLOCK (veto)
        if any(r.verdict == Verdict.BLOCK for r in results):
            final_verdict = Verdict.BLOCK
        # Rule 2: 3+ HOLDs = HOLD
        elif sum(1 for r in results if r.verdict == Verdict.HOLD) >= 3:
            final_verdict = Verdict.HOLD
        # Rule 3: 1-2 HOLDs = HOLD (Wait, TRIAGE Rule 3 says PASS with warnings if 1-2 HOLDs?
        # Actually R-rule 3 says 'PASS con warnings', but let's be safe and HOLD if any significant risk)
        elif any(r.verdict == Verdict.HOLD for r in results):
            final_verdict = Verdict.HOLD
        else:
            final_verdict = Verdict.PASS

        # Triage Score (Weighted average)
        # F1: 30%, F2: 25%, F3: 20%, F4: 15%, F5: 10%
        weights = {"F1": 0.30, "F2": 0.25, "F3": 0.20, "F4": 0.15, "F5": 0.10}
        total_score = 0.0
        for res in results:
            total_score += res.score * weights.get(res.filter_id, 0.05)

        # Blast Radius extraction
        blast_radius = next(
            (r.metadata.get("blast_radius", 0.0) for r in results if r.filter_id == "F1"), 0.0
        )

        # Immunity Certificate
        immunity_cert = final_verdict == Verdict.PASS and total_score > 80.0

        risks = [r.justification for r in results if r.verdict != Verdict.PASS]

        report = TriageReport(
            verdict=final_verdict,
            triage_score=total_score,
            filter_results=results,
            blast_radius=blast_radius,
            immunity_certificate=immunity_cert,
            risks_assumed=risks,
            cortex_persistence=final_verdict != Verdict.PASS,
        )

        logger.info(f"Triage complete: {final_verdict.value} (Score: {total_score:.1f})")
        return report
