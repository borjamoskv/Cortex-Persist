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
from cortex.immune.filters.entropic_quarantine import EntropicQuarantineFilter
from cortex.immune.filters.entropy import EntropyFilter
from cortex.immune.filters.reversibility import ReversibilityFilter

logger = logging.getLogger("cortex.immune.membrane")


@dataclass(frozen=True)
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
    """A membrane with 6 layers that intercepts and validates signals."""

    def __init__(self, engine: Any = None):
        self._engine = engine
        self._background_tasks: set[asyncio.Task] = set()
        self._filters: list[ImmuneFilter] = [
            ReversibilityFilter(),
            AdversarialFilter(),
            CausalFilter(),
            EntropyFilter(),
            ConfidenceFilter(),
            EntropicQuarantineFilter(),
        ]
        self._weights = {"F1": 0.25, "F2": 0.20, "F3": 0.20, "F4": 0.15, "F5": 0.10, "F6": 0.10}

    async def intercept(
        self,
        intent: Any,
        context: dict[str, Any],
    ) -> TriageReport:
        """Evaluate a proposed intent against all immunological filters in parallel."""
        logger.info("Intercepting intent: %s", intent)

        results = await asyncio.gather(
            *(f.evaluate(intent, context) for f in self._filters),
            return_exceptions=True,
        )

        filter_results = [
            res
            if not isinstance(res, Exception)
            else FilterResult(
                filter_id="IMMUNE_ERROR",
                verdict=Verdict.BLOCK,
                score=0,
                justification=f"Filter error: {res}",
            )
            for res in results
        ]

        report = self._triage(filter_results)  # type: ignore[type-error]

        if report.cortex_persistence and self._engine:
            task = asyncio.create_task(self._persist_triage(intent, report))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return report

    async def _persist_triage(self, intent: Any, report: TriageReport) -> None:
        """Sovereign Ledger Persistence (O(1))."""
        try:
            content = f"Membrane Triage: {report.verdict.value}. Score: {report.triage_score:.1f}"
            meta = {
                "triage_score": report.triage_score,
                "blast_radius": report.blast_radius,
                "risks_assumed": report.risks_assumed,
            }
            if isinstance(intent, str):
                meta["intent"] = intent[:1000]

            await self._engine.store(
                tenant_id="sovereign",
                project="membrane",
                content=content,
                fact_type="ghost" if report.verdict.value == Verdict.HOLD else "error",
                tags=["immune_system", "autonomous_intercept"],
                confidence="C4",
                source="membrane",
                meta=meta,
            )
            logger.info("TriageReport autonomously persisted to Ledger.")
        except Exception as e:
            logger.error("Failed to autonomously persist TriageReport: %s", e)

    def _triage(self, results: list[FilterResult]) -> TriageReport:
        """Consolidate the results from the filters."""
        has_block = any(r.verdict == Verdict.BLOCK for r in results)
        holds = sum(1 for r in results if r.verdict == Verdict.HOLD)

        # Determine Verdict: Block > Multiple Holds > Single Hold > Pass
        if has_block:
            final_verdict = Verdict.BLOCK
        elif holds > 0:
            final_verdict = Verdict.HOLD
        else:
            final_verdict = Verdict.PASS

        # O(1) Score calculation
        total_score = sum(r.score * self._weights.get(r.filter_id, 0.05) for r in results)

        blast_radius = next(
            (r.metadata.get("blast_radius", 0.0) for r in results if r.filter_id == "F1"),
            0.0,
        )

        report = TriageReport(
            verdict=final_verdict,
            triage_score=total_score,
            filter_results=results,
            blast_radius=blast_radius,
            immunity_certificate=(final_verdict == Verdict.PASS and total_score > 80.0),
            risks_assumed=[r.justification for r in results if r.verdict != Verdict.PASS],
            cortex_persistence=(final_verdict != Verdict.PASS),
        )

        logger.info("Triage complete: %s (Score: %.1f)", final_verdict.value, total_score)
        return report
