"""CORTEX Metering — Metering Middleware.

Intercepts /v1/* API requests to track usage per authenticated tenant
and enforce quota limits based on their billing plan.
"""

from __future__ import annotations
from typing import Optional

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex.extensions.metering.quotas import QuotaEnforcer
from cortex.extensions.metering.tracker import UsageTracker

__all__ = ["MeteringMiddleware"]

logger = logging.getLogger(__name__)

# Paths that should NOT be metered (health, docs, billing, onboarding)
_EXCLUDED_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/v1/stripe",
    "/v1/signup",
    "/v1/usage",
)


class MeteringMiddleware(BaseHTTPMiddleware):
    """Tracks API consumption per tenant and enforces quota limits.

    Injects ``X-RateLimit-Remaining`` and ``X-RateLimit-Limit`` headers
    into responses for developer visibility.
    """

    def __init__(self, app, tracker: Optional[UsageTracker] = None):
        super().__init__(app)
        self._tracker = tracker or UsageTracker()
        self._enforcer = QuotaEnforcer(self._tracker)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-API and excluded paths
        if not path.startswith("/v1/") or any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)

        # Extract tenant from auth result (set by auth dependency)
        tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
        plan = getattr(getattr(request, "state", None), "plan", "free")

        # If no tenant identified (unauthenticated), let the auth layer handle it
        if not tenant_id:
            return await call_next(request)

        # ── Quota Check ──
        check = self._enforcer.check(tenant_id, plan)
        if not check.allowed:
            logger.warning(
                "Quota exceeded: tenant=%s plan=%s used=%d limit=%d",
                tenant_id,
                plan,
                check.used,
                check.limit,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "quota_exceeded",
                    "detail": (
                        f"Monthly API quota exhausted ({check.limit} calls). "
                        "Upgrade your plan at https://cortex.moskv.com/pricing"
                    ),
                    "used": check.used,
                    "limit": check.limit,
                    "reset_at": check.reset_at,
                },
                headers={
                    "X-RateLimit-Limit": str(check.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": check.reset_at,
                    "Retry-After": "86400",
                },
            )

        # ── Process Request ──
        response = await call_next(request)

        # ── Estimate Tokens ──
        tokens = _estimate_tokens(request, response)

        # ── Record Usage ──
        try:
            self._tracker.record_call(
                tenant_id=tenant_id,
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                tokens_used=tokens,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to record usage for tenant %s", tenant_id)

        # ── Inject Usage Headers ──
        if check.limit > 0:
            response.headers["X-RateLimit-Limit"] = str(check.limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, check.remaining - 1))
            response.headers["X-RateLimit-Reset"] = check.reset_at

        return response


def _estimate_tokens(request: Request, response) -> int:
    """Estimate token usage from request/response.

    Priority:
      1. Explicit X-Tokens-Used header (set by routes that know exact count)
      2. Content-length heuristic (~4 chars per token)
    """
    # Route-provided exact count
    explicit = response.headers.get("X-Tokens-Used")
    if explicit and explicit.isdigit():
        return int(explicit)

    # Heuristic: estimate from content length (~4 chars/token)
    content_len = 0
    cl_header = response.headers.get("content-length")
    if cl_header and cl_header.isdigit():
        content_len = int(cl_header)

    # For POST (store/search), also account for request body size
    if request.method == "POST":
        req_cl = request.headers.get("content-length")
        if req_cl and req_cl.isdigit():
            content_len += int(req_cl)

    return max(1, content_len // 4)
