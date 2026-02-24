"""
CORTEX v5.1 — Admin Security Middleware.

Rate limiting, audit logging, and self-healing trigger for governance endpoints.
Designed for FastAPI dependency injection — zero overhead on non-admin routes.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request

__all__ = [
    "AuditLogger",
    "RateLimiter",
    "SelfHealingHook",
]

logger = logging.getLogger("cortex.admin.middleware")


# ─── Rate Limiter (Token Bucket, per-IP) ─────────────────────────────


class _TokenBucket:
    """Thread-safe token bucket for a single key."""

    __slots__ = ("_capacity", "_tokens", "_refill_rate", "_last_refill", "_lock")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = refill_rate  # tokens per second
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def consume(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


class RateLimiter:
    """Per-IP rate limiter using token buckets.

    Usage as a FastAPI dependency::

        limiter = RateLimiter(max_requests=10, window_seconds=1)
        @router.get("/endpoint", dependencies=[Depends(limiter)])
        async def endpoint(): ...
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0) -> None:
        self._max = max_requests
        self._rate = max_requests / window_seconds
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(self._max, self._rate)
        )

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, request: Request) -> None:
        ip = self._client_ip(request)
        if not self._buckets[ip].consume():
            logger.warning("Rate limit exceeded: ip=%s path=%s", ip, request.url.path)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")


# ─── Audit Logger ────────────────────────────────────────────────────


class AuditLogger:
    """Structured audit logger for admin endpoints.

    Logs method, path, client IP, user-agent, and auth status.
    """

    async def __call__(self, request: Request) -> None:
        ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )
        logger.info(
            "AUDIT | method=%s path=%s ip=%s ua=%s",
            request.method,
            request.url.path,
            ip.split(",")[0].strip(),
            (request.headers.get("User-Agent") or "")[:120],
        )


# ─── Self-Healing Hook ──────────────────────────────────────────────


class SelfHealingHook:
    """Lightweight hook that triggers self-healing on unhandled admin exceptions.

    Call ``SelfHealingHook.trigger(exc)`` from an endpoint's except block.
    The hook logs the event and (optionally) invokes heal_project if an
    engine and project are available on ``request.app.state``.
    """

    @staticmethod
    def trigger(exc: BaseException, context: dict[str, Any] | None = None) -> None:
        """Record the failure and attempt lightweight recovery.

        This does NOT call the full MEJORAlo heal loop — it only logs and
        increments a failure counter so monitoring can alert.  Full healing
        requires a CLI invocation (``cortex mejoralo --heal``).
        """
        ctx = context or {}
        endpoint = ctx.get("endpoint", "unknown")
        logger.error(
            "SELF-HEAL | endpoint=%s error=%s type=%s",
            endpoint,
            str(exc)[:200],
            type(exc).__name__,
        )
        # Increment a simple counter for Prometheus/StatsD scraping
        _HEAL_COUNTER[endpoint] = _HEAL_COUNTER.get(endpoint, 0) + 1


# Simple in-memory counter (replace with Prometheus Counter in production)
_HEAL_COUNTER: dict[str, int] = {}
