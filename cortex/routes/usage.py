"""CORTEX v6.0 — Usage Router.

Exposes API consumption metrics to authenticated tenants.
Enables developers to track their usage and plan limits.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request

from cortex.auth import AuthResult, require_permission
from cortex.extensions.metering.quotas import QuotaEnforcer
from cortex.extensions.metering.tracker import UsageTracker

__all__ = ["get_tracker", "get_usage", "get_usage_breakdown", "get_usage_history"]

router = APIRouter(prefix="/v1/usage", tags=["usage"])
logger = logging.getLogger(__name__)

# FastAPI dependency — lazily initialized, overridable in tests
_tracker: Optional[UsageTracker] = None


def get_tracker() -> UsageTracker:
    """FastAPI dependency for UsageTracker (singleton, overridable)."""
    global _tracker  # noqa: PLW0603
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


@router.get("")
async def get_usage(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    tracker: UsageTracker = Depends(get_tracker),
) -> dict:
    """Get current month's API usage for the authenticated tenant."""
    enforcer = QuotaEnforcer(tracker)

    plan = getattr(auth, "plan", "free") or "free"
    usage = tracker.get_usage(auth.tenant_id)
    check = enforcer.check(auth.tenant_id, plan)
    plan_info = enforcer.get_plan_info(plan)

    return {
        "tenant_id": auth.tenant_id,
        "plan": plan,
        "period": usage["month"],
        "calls_used": usage["calls_used"],
        "calls_limit": plan_info["calls_limit"],
        "calls_remaining": check.remaining,
        "tokens_used": usage["tokens_used"],
        "projects_limit": plan_info["projects_limit"],
        "storage_limit_bytes": plan_info["storage_bytes"],
        "reset_at": check.reset_at,
        "last_call_at": usage["last_call_at"],
    }


@router.get("/history")
async def get_usage_history(
    request: Request,
    months: int = 12,
    auth: AuthResult = Depends(require_permission("read")),
    tracker: UsageTracker = Depends(get_tracker),
) -> dict:
    """Get usage history for the last N months."""
    history = tracker.get_usage_history(auth.tenant_id, months=months)

    return {
        "tenant_id": auth.tenant_id,
        "months": history,
    }


@router.get("/breakdown")
async def get_usage_breakdown(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    tracker: UsageTracker = Depends(get_tracker),
) -> dict:
    """Get per-endpoint breakdown for current month."""
    breakdown = tracker.get_endpoint_breakdown(auth.tenant_id)

    return {
        "tenant_id": auth.tenant_id,
        "endpoints": breakdown,
    }
