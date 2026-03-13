"""CORTEX v6.0 — Developer Onboarding Router.

Self-service signup flow for Memory-as-a-Service.
Creates tenant, provisions free-tier API key, returns quickstart info.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

__all__ = ["SignupRequest", "SignupResponse", "signup"]

router = APIRouter(prefix="/v1", tags=["onboarding"])
logger = logging.getLogger(__name__)


class SignupRequest(BaseModel):
    """Self-service signup request."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=128, description="Display name or org name")


class SignupResponse(BaseModel):
    """Signup result with API credentials."""

    api_key: str
    tenant_id: str
    plan: str
    calls_limit: int
    quickstart_url: str
    message: str


@router.post("/signup", response_model=SignupResponse)
async def signup(req: SignupRequest) -> SignupResponse:
    """Create a free-tier account. Returns API key immediately.

    No email verification required for MVP — key is active on creation.
    """
    import cortex.api.state as api_state

    if not api_state.auth_manager:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    # Check for duplicate signups by email (tenant_id = email)
    existing_keys = await api_state.auth_manager.list_keys(tenant_id=req.email)
    if existing_keys:
        raise HTTPException(
            status_code=409,
            detail=f"Account already exists for {req.email}. "
            "Use your existing API key or contact support.",
        )

    # Create API key with free tier permissions
    try:
        raw_key, _api_key = await api_state.auth_manager.create_key(
            name=f"free-{req.name}",
            tenant_id=req.email,
            role="user",
            permissions=["read", "write"],
            rate_limit=30,  # Free tier: 30 req/min
        )
    except (RuntimeError, ValueError, OSError) as e:
        logger.exception("Signup failed for %s", req.email)
        raise HTTPException(status_code=500, detail="Failed to create account") from e

    logger.info("New signup: %s → tenant=%s plan=free", req.name, req.email)

    # Get plan limits from quota system (single source of truth)
    from cortex.metering.quotas import QuotaEnforcer
    from cortex.metering.tracker import UsageTracker

    plan_info = QuotaEnforcer(UsageTracker()).get_plan_info("free")

    return SignupResponse(
        api_key=raw_key,
        tenant_id=req.email,
        plan="free",
        calls_limit=plan_info["calls_limit"],
        quickstart_url="https://docs.cortex.moskv.com/quickstart",
        message=f"Welcome, {req.name}! Your free-tier API key is ready. "
        "Store it securely — it won't be shown again.",
    )
