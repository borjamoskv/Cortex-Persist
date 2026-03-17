"""CORTEX Revenue Engine — Data Models.

Defines the core data structures for opportunities, execution results,
revenue reports, and the pluggable vector protocol.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class OpportunityStatus(Enum):
    """Lifecycle states for a revenue opportunity."""

    DETECTED = "detected"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class VectorType(Enum):
    """Revenue vector identifiers."""

    MICROSAAS = "microsaas"
    ARBITRAGE = "arbitrage"
    OUTREACH = "outreach"


@dataclass
class Opportunity:
    """A detected revenue opportunity.

    Attributes:
        id: Unique identifier (UUID hex).
        vector: Which revenue vector discovered this.
        title: Human-readable title.
        description: Detailed description of the opportunity.
        estimated_value: Estimated revenue in EUR.
        confidence: C1-C5 epistemic confidence.
        effort_hours: Estimated effort to execute.
        status: Current lifecycle status.
        source_url: Where the opportunity was found.
        meta: Arbitrary metadata (vector-specific).
        created_at: ISO timestamp of detection.
    """

    vector: VectorType
    title: str
    description: str
    estimated_value: Decimal = Decimal("0")
    confidence: str = "C3"
    effort_hours: float = 1.0
    status: OpportunityStatus = OpportunityStatus.DETECTED
    source_url: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def roi_score(self) -> float:
        """ROI = estimated_value / effort_hours. Higher is better."""
        if self.effort_hours <= 0:
            return float("inf")
        return float(self.estimated_value) / self.effort_hours

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for CORTEX storage."""
        return {
            "id": self.id,
            "vector": self.vector.value,
            "title": self.title,
            "description": self.description,
            "estimated_value": str(self.estimated_value),
            "confidence": self.confidence,
            "effort_hours": self.effort_hours,
            "status": self.status.value,
            "source_url": self.source_url,
            "meta": self.meta,
            "roi_score": self.roi_score,
            "created_at": self.created_at,
        }


@dataclass
class ExecutionResult:
    """Outcome of executing a revenue opportunity.

    Attributes:
        opportunity_id: The opportunity that was executed.
        success: Whether execution completed successfully.
        revenue_actual: Actual revenue generated (EUR).
        cost_actual: Actual costs incurred (EUR).
        artifact_url: URL of the deployed artifact (if any).
        error: Error message if failed.
        duration_seconds: How long execution took.
        meta: Execution-specific metadata.
    """

    opportunity_id: str
    success: bool
    revenue_actual: Decimal = Decimal("0")
    cost_actual: Decimal = Decimal("0")
    artifact_url: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def net_profit(self) -> Decimal:
        """Net profit = revenue - cost."""
        return self.revenue_actual - self.cost_actual

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for CORTEX storage."""
        return {
            "opportunity_id": self.opportunity_id,
            "success": self.success,
            "revenue_actual": str(self.revenue_actual),
            "cost_actual": str(self.cost_actual),
            "net_profit": str(self.net_profit),
            "artifact_url": self.artifact_url,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "meta": self.meta,
            "executed_at": self.executed_at,
        }


@dataclass
class RevenueReport:
    """Daily/weekly P&L summary across all vectors.

    Attributes:
        period: Report period label (e.g., "2026-03-13", "2026-W11").
        total_opportunities: Number of opportunities detected.
        total_executed: Number of opportunities executed.
        total_revenue: Cumulative revenue (EUR).
        total_cost: Cumulative costs (EUR).
        by_vector: Breakdown by vector type.
    """

    period: str
    total_opportunities: int = 0
    total_executed: int = 0
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    by_vector: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def net_profit(self) -> Decimal:
        """Net profit across all vectors."""
        return self.total_revenue - self.total_cost

    @property
    def success_rate(self) -> float:
        """Execution success rate as a percentage."""
        if self.total_executed == 0:
            return 0.0
        successful = sum(1 for v in self.by_vector.values() if v.get("successful", 0) > 0)
        return (successful / self.total_executed) * 100


@runtime_checkable
class RevenueVector(Protocol):
    """Protocol for pluggable revenue vectors.

    Each vector implements its own scanning and execution logic.
    The RevenueEngine orchestrates them uniformly.
    """

    @property
    def id(self) -> VectorType:
        """Unique vector identifier."""
        ...

    @property
    def name(self) -> str:
        """Human-readable vector name."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this vector is currently active."""
        ...

    async def scan(self) -> list[Opportunity]:
        """Scan for new revenue opportunities.

        Returns:
            List of detected opportunities, scored and ready for evaluation.
        """
        ...

    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Execute a specific opportunity through this vector's pipeline.

        Args:
            opportunity: The opportunity to execute.

        Returns:
            Execution result with actual revenue/cost data.
        """
        ...
