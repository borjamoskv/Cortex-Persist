"""
CORTEX v5.1 — Edge Security & Traffic Middleware.

Separated from `api.py` to maintain architectural limits (<300 LOC per file)
and consolidate defensive mechanisms in a single Sovereign module (KETER-∞).
"""

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans

logger = logging.getLogger("uvicorn.error")


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Prevents large payload attacks by limiting request body size."""

    def __init__(self, app, max_size: int = 1_048_576):  # 1MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                logger.warning(
                    "Payload too large: %s from %s",
                    content_length,
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload too large. Max 1MB allowed."},
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects industry-standard security headers for defense-in-depth."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Content-Security-Policy"] = "default-src 'self'"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter (Sliding Window, bounded).
    Prioritizes Auth Key IDs over Client IPs for bucket generation.
    """

    MAX_TRACKED_ENTITIES: Final[int] = 10_000

    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.buckets: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        client_ip = request.client.host if request.client else "unknown"

        # Priority mapping: Key ID > IP
        bucket_id = client_ip
        if auth_header.startswith("Bearer "):
            bucket_id = f"key:{auth_header[7:19]}"

        now = time.time()

        if bucket_id not in self.buckets:
            # Enforce capacity
            if len(self.buckets) >= self.MAX_TRACKED_ENTITIES:
                self._evict(now)
            self.buckets[bucket_id] = deque()

        timestamps = self.buckets[bucket_id]

        # Slide window
        while timestamps and now - timestamps[0] > self.window:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
            logger.warning("Rate limit exceeded for %s", bucket_id)
            return JSONResponse(
                status_code=429,
                content={"detail": get_trans("error_too_many_requests", lang)},
                headers={"Retry-After": str(self.window)},
            )

        timestamps.append(now)
        return await call_next(request)

    def _evict(self, now: float) -> None:
        """Deterministic eviction of stale or excess buckets."""
        # 1. Delete truly expired
        expired = [bid for bid, ts in self.buckets.items() if not ts or now - ts[-1] > self.window]
        for bid in expired:
            del self.buckets[bid]

        # 2. Hard trim if still over capacity (20% reduction)
        if len(self.buckets) >= self.MAX_TRACKED_ENTITIES:
            by_recency = sorted(
                self.buckets.keys(), key=lambda k: self.buckets[k][-1] if self.buckets[k] else 0
            )
            for bid in by_recency[: len(by_recency) // 5]:
                del self.buckets[bid]


class SecurityFraudMiddleware(BaseHTTPMiddleware):
    """
    Zero-Trust Edge Middleware (Defensive Network Layer).
    Intercepts anomalous responses (4xx, 5xx), extracts the attack signature,
    and asynchronously writes it to the firewall log so the Daemon's L2 Vectorizer
    can correlate the anomaly mathematically.
    """

    def __init__(self, app, log_path: str = "~/.cortex/firewall.log"):
        super().__init__(app)
        self.log_path = Path(log_path).expanduser()
        self._bg_tasks = set()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # 1. Hardware-level Blacklist Check
        if await self._is_blacklisted(request, client_ip):
            logger.warning(
                "🛡️ KILL SWITCH ENGAGED: Connection dropped for blacklisted IP: %s",
                client_ip,
            )
            return JSONResponse(status_code=403, content={"error": "Access Denied"})

        # 2. Continue with the request handling
        response = await call_next(request)

        # 3. Anomaly detection and logging
        if response.status_code >= 400:
            self._log_security_event(request, response, client_ip)

        return response

    async def _is_blacklisted(self, request: Request, client_ip: str) -> bool:
        """Check if IP is in threat intel database."""
        if client_ip == "unknown":
            return False

        pool = getattr(request.app.state, "pool", None)
        if not pool:
            return False

        try:
            async with pool.acquire() as conn:
                now = datetime.now(timezone.utc).isoformat()
                sql = "SELECT 1 FROM threat_intel WHERE ip_address = ? AND (expires_at IS NULL OR expires_at > ?)"
                async with conn.execute(sql, (client_ip, now)) as cursor:
                    return bool(await cursor.fetchone())
        except Exception as e:
            logger.error("ThreatIntel check failed: %s", e)
            return False

    def _log_security_event(self, request: Request, response: Any, client_ip: str) -> None:
        """Log suspicious response to firewall log asynchronously."""
        signature = (
            f"[{request.method}] {request.url.path} "
            f"| UA: {request.headers.get('user-agent', 'unknown')} "
            f"| Status: {response.status_code}"
        )

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": client_ip,
            "status_code": response.status_code,
            "payload": signature,
        }

        def _write():
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except OSError:
                pass

        task = asyncio.create_task(asyncio.to_thread(_write))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
