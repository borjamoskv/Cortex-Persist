"""CORTEX Metering — Quota Enforcement.

Plan-based quota definitions and enforcement for Memory-as-a-Service.
Integrates with UsageTracker to check consumption against plan limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cortex.metering.tracker import UsageTracker

__all__ = ["PLAN_QUOTAS", "QuotaCheckResult", "QuotaEnforcer"]

logger = logging.getLogger(__name__)


# ─── Plan Definitions ────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanQuota:
    """Immutable quota definition for a billing plan."""

    name: str
    calls_limit: int  # Monthly API call limit (-1 = unlimited)
    projects_limit: int  # Max projects (-1 = unlimited)
    storage_bytes: int  # Max storage in bytes (-1 = unlimited)
    rate_limit: int  # Requests per minute
    search_depth: int  # Max graph_depth for search
    batch_size: int  # Max items per batch request
    ledger_verify: bool  # Can verify ledger integrity


PLAN_QUOTAS: dict[str, PlanQuota] = {
    "free": PlanQuota(
        name="free",
        calls_limit=1_000,
        projects_limit=1,
        storage_bytes=10 * 1024 * 1024,  # 10MB
        rate_limit=30,
        search_depth=1,
        batch_size=10,
        ledger_verify=False,
    ),
    "pro": PlanQuota(
        name="pro",
        calls_limit=50_000,
        projects_limit=10,
        storage_bytes=1024 * 1024 * 1024,  # 1GB
        rate_limit=300,
        search_depth=3,
        batch_size=100,
        ledger_verify=True,
    ),
    "team": PlanQuota(
        name="team",
        calls_limit=500_000,
        projects_limit=-1,
        storage_bytes=-1,
        rate_limit=1_000,
        search_depth=5,
        batch_size=500,
        ledger_verify=True,
    ),
}


# ─── Quota Check Result ──────────────────────────────────────────────


@dataclass
class QuotaCheckResult:
    """Result of a quota check."""

    allowed: bool
    remaining: int
    limit: int
    used: int
    plan: str
    reset_at: str  # ISO timestamp of month reset


# ─── Enforcer ────────────────────────────────────────────────────────


class QuotaEnforcer:
    """Enforces plan-based quotas against tracked usage.

    Args:
        tracker: UsageTracker instance for reading consumption data.
    """

    def __init__(self, tracker: UsageTracker):
        self._tracker = tracker

    def check(
        self,
        tenant_id: str,
        plan: str = "free",
    ) -> QuotaCheckResult:
        """Check if a tenant has remaining quota for their plan.

        Returns:
            QuotaCheckResult with allowed flag and remaining calls.
        """
        quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
        usage = self._tracker.get_usage(tenant_id)
        calls_used = usage["calls_used"]

        # Unlimited plan
        if quota.calls_limit == -1:
            return QuotaCheckResult(
                allowed=True,
                remaining=-1,
                limit=-1,
                used=calls_used,
                plan=plan,
                reset_at=self._next_reset(),
            )

        remaining = max(0, quota.calls_limit - calls_used)

        return QuotaCheckResult(
            allowed=remaining > 0,
            remaining=remaining,
            limit=quota.calls_limit,
            used=calls_used,
            plan=plan,
            reset_at=self._next_reset(),
        )

    def get_plan_info(self, plan: str = "free") -> dict[str, Any]:
        """Get quota information for a plan."""
        quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
        return {
            "plan": quota.name,
            "calls_limit": quota.calls_limit,
            "projects_limit": quota.projects_limit,
            "storage_bytes": quota.storage_bytes,
            "rate_limit": quota.rate_limit,
            "search_depth": quota.search_depth,
            "batch_size": quota.batch_size,
            "ledger_verify": quota.ledger_verify,
        }

    @staticmethod
    def _next_reset() -> str:
        """Calculate the next monthly reset timestamp (1st of next month, 00:00 UTC)."""
        now = datetime.now(timezone.utc)
        if now.month == 12:
            reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0)
        else:
            reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0)
        return reset.isoformat()
