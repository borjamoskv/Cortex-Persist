"""CORTEX Revenue Engine — Sovereign Revenue Orchestrator.

Coordinates multiple revenue vectors, evaluates opportunities by ROI,
persists results to the CORTEX ledger, and generates P&L reports.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from cortex.revenue.models import (
    ExecutionResult,
    Opportunity,
    OpportunityStatus,
    RevenueReport,
    RevenueVector,
    VectorType,
)

logger = logging.getLogger("cortex.revenue.engine")


class RevenueEngine:
    """Sovereign Revenue Orchestrator.

    Runs all registered vectors in parallel, evaluates and ranks
    opportunities by ROI, and executes them through their respective
    pipelines. All results are persisted to CORTEX for audit.

    Attributes:
        vectors: Mapping of vector type to vector instance.
        opportunities: All detected opportunities (current session).
        results: All execution results (current session).
    """

    def __init__(
        self,
        vectors: list[RevenueVector] | None = None,
        auto_execute: bool = False,
        min_roi: float = 5.0,
    ) -> None:
        """Initialize the revenue engine.

        Args:
            vectors: List of revenue vector implementations.
            auto_execute: If True, automatically execute approved opportunities.
                         Default False for safety.
            min_roi: Minimum ROI score to consider an opportunity viable.
        """
        self.vectors: dict[VectorType, RevenueVector] = {}
        if vectors:
            for v in vectors:
                self.vectors[v.id] = v

        self.auto_execute = auto_execute
        self.min_roi = min_roi
        self.opportunities: list[Opportunity] = []
        self.results: list[ExecutionResult] = []

    def register_vector(self, vector: RevenueVector) -> None:
        """Register a new revenue vector.

        Args:
            vector: Vector implementation conforming to RevenueVector protocol.
        """
        self.vectors[vector.id] = vector
        logger.info("📈 [DINERO] Registered vector: %s", vector.name)

    async def scan(self, dry_run: bool = False) -> list[Opportunity]:
        """Scan all active vectors for revenue opportunities.

        Runs each vector's scan() method concurrently. Filters by enabled
        status and minimum ROI threshold.

        Args:
            dry_run: If True, skip persistence. Useful for testing.

        Returns:
            Sorted list of opportunities (highest ROI first).
        """
        active = [v for v in self.vectors.values() if v.enabled]
        if not active:
            logger.warning("⚠️ [DINERO] No active vectors registered.")
            return []

        logger.info(
            "🔍 [DINERO] Scanning %d vectors: %s",
            len(active),
            ", ".join(v.name for v in active),
        )

        # Run all scans concurrently
        tasks = [v.scan() for v in active]
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_opportunities: list[Opportunity] = []
        for vector, result in zip(active, scan_results):
            if isinstance(result, BaseException):
                logger.error(
                    "☠️ [DINERO] Vector %s scan failed: %s",
                    vector.name,
                    result,
                )
                continue
            all_opportunities.extend(result)

        # Filter by minimum ROI
        viable = [
            opp for opp in all_opportunities if opp.roi_score >= self.min_roi
        ]

        # Sort by ROI descending
        viable.sort(key=lambda o: o.roi_score, reverse=True)

        # Mark as evaluated
        for opp in viable:
            opp.status = OpportunityStatus.EVALUATED

        self.opportunities.extend(viable)

        if not dry_run:
            await self._persist_opportunities(viable)

        logger.info(
            "💰 [DINERO] Found %d viable opportunities (of %d total scanned).",
            len(viable),
            len(all_opportunities),
        )
        return viable

    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Execute a single opportunity through its vector pipeline.

        Args:
            opportunity: The opportunity to execute.

        Returns:
            Execution result with actual revenue/cost data.

        Raises:
            ValueError: If the opportunity's vector is not registered.
        """
        vector = self.vectors.get(opportunity.vector)
        if not vector:
            raise ValueError(
                f"Vector {opportunity.vector.value!r} not registered."
            )

        opportunity.status = OpportunityStatus.EXECUTING
        logger.info(
            "🚀 [DINERO] Executing: %s (vector=%s, est=€%s)",
            opportunity.title,
            vector.name,
            opportunity.estimated_value,
        )

        start = time.monotonic()
        try:
            result = await vector.execute(opportunity)
            result.duration_seconds = time.monotonic() - start

            if result.success:
                opportunity.status = OpportunityStatus.COMPLETED
                logger.info(
                    "✅ [DINERO] Success: %s → €%s net profit",
                    opportunity.title,
                    result.net_profit,
                )
            else:
                opportunity.status = OpportunityStatus.FAILED
                logger.warning(
                    "❌ [DINERO] Failed: %s → %s",
                    opportunity.title,
                    result.error,
                )
        except Exception as e:
            opportunity.status = OpportunityStatus.FAILED
            result = ExecutionResult(
                opportunity_id=opportunity.id,
                success=False,
                error=str(e),
                duration_seconds=time.monotonic() - start,
            )
            logger.error(
                "☠️ [DINERO] Execution crashed: %s → %s",
                opportunity.title,
                e,
            )

        self.results.append(result)
        await self._persist_result(result)
        return result

    async def execute_all(
        self,
        opportunities: list[Opportunity] | None = None,
        max_concurrent: int = 3,
    ) -> list[ExecutionResult]:
        """Execute multiple opportunities with concurrency control.

        Args:
            opportunities: Opportunities to execute. Defaults to all evaluated
                          opportunities from the last scan.
            max_concurrent: Maximum concurrent executions.

        Returns:
            List of execution results.
        """
        targets = opportunities or [
            o
            for o in self.opportunities
            if o.status == OpportunityStatus.EVALUATED
        ]

        if not targets:
            logger.info("📭 [DINERO] No opportunities to execute.")
            return []

        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[ExecutionResult] = []

        async def _bounded_execute(opp: Opportunity) -> ExecutionResult:
            async with semaphore:
                return await self.execute(opp)

        tasks = [_bounded_execute(opp) for opp in targets]
        results = await asyncio.gather(*tasks)  # type: ignore[assignment]
        return list(results)

    def report(self, period: str | None = None) -> RevenueReport:
        """Generate a P&L report for the current session.

        Args:
            period: Report period label. Defaults to today's date.

        Returns:
            Revenue report with breakdown by vector.
        """
        period = period or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        by_vector: dict[str, dict[str, Any]] = {}
        total_revenue = Decimal("0")
        total_cost = Decimal("0")
        total_executed = 0

        for result in self.results:
            # Find the opportunity to get the vector
            opp = next(
                (o for o in self.opportunities if o.id == result.opportunity_id),
                None,
            )
            vector_key = opp.vector.value if opp else "unknown"

            if vector_key not in by_vector:
                by_vector[vector_key] = {
                    "executed": 0,
                    "successful": 0,
                    "revenue": Decimal("0"),
                    "cost": Decimal("0"),
                }

            entry = by_vector[vector_key]
            entry["executed"] += 1
            total_executed += 1

            if result.success:
                entry["successful"] += 1
                entry["revenue"] += result.revenue_actual
                entry["cost"] += result.cost_actual
                total_revenue += result.revenue_actual
                total_cost += result.cost_actual

        # Serialize Decimals for JSON compatibility
        for entry in by_vector.values():
            entry["revenue"] = str(entry["revenue"])
            entry["cost"] = str(entry["cost"])

        return RevenueReport(
            period=period,
            total_opportunities=len(self.opportunities),
            total_executed=total_executed,
            total_revenue=total_revenue,
            total_cost=total_cost,
            by_vector=by_vector,
        )

    async def _persist_opportunities(
        self, opportunities: list[Opportunity]
    ) -> None:
        """Persist detected opportunities to CORTEX ledger."""
        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            for opp in opportunities:
                await engine.store(
                    content=f"[DINERO] Opportunity: {opp.title}",
                    fact_type="discovery",
                    project="dinero",
                    tags=["revenue", opp.vector.value, opp.confidence],
                    confidence=opp.confidence,
                    source="agent:dinero",
                    meta=opp.to_dict(),
                )
        except ImportError:
            logger.debug("CORTEX engine not available, skipping persistence.")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to persist opportunities: %s", e)

    async def _persist_result(self, result: ExecutionResult) -> None:
        """Persist execution result to CORTEX ledger."""
        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            fact_type = "decision" if result.success else "error"
            await engine.store(
                content=(
                    f"[DINERO] Execution {'✅' if result.success else '❌'}: "
                    f"€{result.net_profit} net"
                ),
                fact_type=fact_type,
                project="dinero",
                tags=["revenue", "execution"],
                confidence="C5" if result.success else "C4",
                source="agent:dinero",
                meta=result.to_dict(),
            )
        except ImportError:
            logger.debug("CORTEX engine not available, skipping persistence.")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to persist result: %s", e)
