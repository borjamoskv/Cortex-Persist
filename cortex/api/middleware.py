"""
CORTEX v5.1 — Edge Security & Traffic Middleware.

Separated from `api.py` to maintain architectural limits (<300 LOC per file)
and consolidate defensive mechanisms in a single Sovereign module (KETER-∞).
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans

logger = logging.getLogger("uvicorn.error")

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class TracingMiddleware(BaseHTTPMiddleware):
    """Generates trace_id and provides structured JSON logging for requests."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(req_id)
        request.state.request_id = req_id

        start_time = time.time()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            process_time = time.time() - start_time
            logger.info(
                json.dumps(
                    {
                        "trace_id": req_id,
                        "event": "request_completed",
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": round(process_time * 1000, 2),
                        "ip": request.client.host if request.client else "unknown",
                    }
                )
            )
            return response
        except Exception as e:  # noqa: BLE001 — tracing middleware must log all failures before raising
            process_time = time.time() - start_time
            logger.error(
                json.dumps(
                    {
                        "trace_id": req_id,
                        "event": "request_failed",
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(process_time * 1000, 2),
                        "error": str(e),
                    }
                )
            )
            raise
        finally:
            request_id_var.reset(token)


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
    """Injects industry-standard security headers for defense-in-depth.

    Headers applied:
        - Content-Security-Policy: restricts resource loading (replaces deprecated X-CSP)
        - Strict-Transport-Security: enforces HTTPS for 1 year with includeSubDomains
        - X-Content-Type-Options: prevents MIME sniffing
        - X-Frame-Options: prevents clickjacking
        - Referrer-Policy: limits referrer leakage
        - Permissions-Policy: disables dangerous browser APIs
        - Cross-Origin-Opener-Policy: isolates browsing context
        - Cache-Control: no-store on sensitive paths
    """

    # Paths that MUST NOT be cached (contain auth tokens, secrets, PII)
    _SENSITIVE_PREFIXES = ("/v1/admin", "/v1/handoff", "/v1/status", "/v1/facts")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Core headers (OWASP recommended)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Sensitive path protection — never cache auth/admin responses
        if any(request.url.path.startswith(p) for p in self._SENSITIVE_PREFIXES):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

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
        self._buffer: deque[str] = deque()
        self._flush_task = None

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Initialize the flusher lazily on the first request to attach it to the current running loop
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flusher())

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

    async def _flusher(self):
        """Single background loop to flush deque to disk without thread spin-up overheads per-request."""
        while True:
            await asyncio.sleep(2.0)
            if not self._buffer:
                continue

            # Batch O(1) extractions against C-routine deque
            lines = []
            while self._buffer:
                lines.append(self._buffer.popleft())

            def _write_all(data_lines):
                try:
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write("".join(data_lines))
                except OSError:
                    pass

            # 1 thread spin-up per interval, not per attack request
            await asyncio.to_thread(_write_all, lines)

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
        except Exception as e:  # noqa: BLE001 — threat intel check failure must not crash request
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

        # O(1) append against C-routine deque. Zero spin-up.
        self._buffer.append(json.dumps(event) + "\n")


class ImmuneMiddleware(BaseHTTPMiddleware):
    """
    Middleware Inmunitario (L1 Sovereign Defense).
    - Prevents data poisoning mathematically before hitting routing.
    - Extracts and establishes Tenant Context for RLS isolation.
    """

    async def dispatch(self, request: Request, call_next):
        from cortex.extensions.security.tenant import tenant_id_var

        # 1. Establish Tenant Context for Database RLS
        # In full production, this is validated by AuthManager from the JWT.
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        token = tenant_id_var.set(tenant_id)

        try:
            # 2. Deep Payload Defense (Poisoning Check)
            if request.method in ("POST", "PUT", "PATCH"):
                body = await request.body()

                try:
                    from cortex.mcp.guard import MCPGuard

                    if MCPGuard.detect_poisoning(body.decode(errors="ignore")):
                        logger.warning(
                            "🛡️ IMMUNE SYSTEM: Poisoning attempt rejected. Tenant: %s", tenant_id
                        )
                        return JSONResponse(
                            status_code=403,
                            content={"error": "Payload rejected by Immune System (Data Poisoning)"},
                        )
                except ImportError:
                    pass

                # Reconstruct stream since we consumed it
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive

            return await call_next(request)
        finally:
            tenant_id_var.reset(token)
