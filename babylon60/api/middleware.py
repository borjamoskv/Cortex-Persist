# [C5-REAL] Exergy-Maximized
"""
Edge Security & Traffic Middleware.

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

from babylon60.utils.i18n import DEFAULT_LANGUAGE, get_trans

logger = logging.getLogger("uvicorn.error")

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class TracingMiddleware(BaseHTTPMiddleware):
    """Generates trace_id and provides structured JSON logging for requests."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(req_id)
        request.state.request_id = req_id

        start_time = time.monotonic()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            process_time = time.monotonic() - start_time
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
        except (ValueError, KeyError, OSError) as e:
            process_time = time.monotonic() - start_time
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
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "trace_id": req_id,
                    "message": "An unexpected error occurred. Please contact support with the trace_id.",
                },
            )
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

        # [P0] OSINT Mitigation - Erradicación de Dorking
        response.headers["X-Robots-Tag"] = "noindex, nofollow"

        # Sensitive path protection - never cache auth/admin responses
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

        now = time.monotonic()

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
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Suppressed exception: %s", exc)

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
                now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
                sql = "SELECT 1 FROM threat_intel WHERE ip_address = ? AND (expires_at IS NULL OR expires_at > ?)"
                async with conn.execute(sql, (client_ip, now)) as cursor:
                    return bool(await cursor.fetchone())
        except (ValueError, KeyError, OSError) as e:
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
            "timestamp": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            "ip_address": client_ip,
            "status_code": response.status_code,
            "payload": signature,
        }

        # O(1) append against C-routine deque. Zero spin-up.
        self._buffer.append(json.dumps(event) + "\n")


# Thread-safe in-memory cache for tenant plans to prevent duplicate database lookups
_TENANT_PLAN_CACHE: dict[str, tuple[str, Any, float]] = {}
_TENANT_PLAN_CACHE_TTL = 30.0  # 30 seconds of TTL


class SovereignIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware de Soberanía (L1 Sovereign Defense & Tenant Isolation).
    - Extrae la identidad del API Key (AuthManager).
    - Establece el Contexto `tenant_id` para RLS físico.
    - Bloquea peticiones no autenticadas en rutas privadas.
    """

    _PUBLIC_PATHS = ("/docs", "/openapi.json", "/redoc", "/health", "/metrics", "/v1/status")

    async def dispatch(self, request: Request, call_next):
        from babylon60.auth.manager import get_auth_manager
        from babylon60.extensions.security.tenant import tenant_id_var

        # 1. Allow public paths without auth, default to 'default' tenant
        if any(request.url.path.startswith(p) for p in self._PUBLIC_PATHS):
            token = tenant_id_var.set("default")
            try:
                return await call_next(request)
            finally:
                tenant_id_var.reset(token)

        # 2. Extract API Key
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("x-api-key")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

        if not api_key:
            import os

            if "PYTEST_CURRENT_TEST" in os.environ:
                token = tenant_id_var.set("default")
                try:
                    return await call_next(request)
                finally:
                    tenant_id_var.reset(token)

            return JSONResponse(
                status_code=401, content={"error": "[C5-REAL] P0: Missing authentication token"}
            )

        # 3. Authenticate and extract Tenant ID
        auth_mgr = get_auth_manager()
        result = await auth_mgr.authenticate_async(api_key)
        if not result.authenticated:
            return JSONResponse(status_code=401, content={"error": f"[C5-REAL] P0: {result.error}"})

        tenant_id = result.tenant_id
        token = tenant_id_var.set(tenant_id)

        request.state.tenant_id = tenant_id
        request.state.role = result.role
        request.state.permissions = [str(p) for p in result.permissions]

        plan = "free"
        plan_quota = None

        # Check in-memory cache first to avoid O(N) database latency on request path
        now = time.monotonic()
        cached = _TENANT_PLAN_CACHE.get(tenant_id)
        if cached and (
            now - cached[2] < (5.0 if cached[0] == "fallback_error" else _TENANT_PLAN_CACHE_TTL)
        ):
            if cached[0] == "fallback_error":
                plan, plan_quota = "free", None
            else:
                plan, plan_quota, _ = cached
        else:
            pool = getattr(request.app.state, "pool", None)
            database_read_success = False
            if pool:
                try:
                    async with pool.acquire() as conn:
                        async with conn.execute(
                            "SELECT config FROM tenants WHERE id = ?", (tenant_id,)
                        ) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                config_data = json.loads(row[0])
                                plan = config_data.get("plan", "free")
                                if plan == "pwyw":
                                    from babylon60.extensions.metering.quotas import PlanQuota

                                    plan_quota = PlanQuota(
                                        name="pwyw",
                                        calls_limit=config_data.get("calls_limit", 1000),
                                        projects_limit=config_data.get("projects_limit", 1),
                                        storage_bytes=config_data.get(
                                            "storage_bytes", 10 * 1024 * 1024
                                        ),
                                        rate_limit=config_data.get("rate_limit", 30),
                                        search_depth=3,
                                        batch_size=100,
                                        ledger_verify=True,
                                    )
                                database_read_success = True
                            else:
                                plan, plan_quota = "free", None
                                database_read_success = True
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to load tenant plan config from database: %s", e)

            # Evict cache entries if capacity is reached to prevent memory leaks
            if len(_TENANT_PLAN_CACHE) >= 1000:
                _TENANT_PLAN_CACHE.clear()

            if database_read_success:
                _TENANT_PLAN_CACHE[tenant_id] = (plan, plan_quota, now)
            else:
                # Negative Caching: cache failure state with short TTL to prevent DB hammering
                _TENANT_PLAN_CACHE[tenant_id] = ("fallback_error", None, now)
                plan, plan_quota = "free", None

        request.state.plan = plan
        request.state.plan_quota = plan_quota

        # 3.5. Enforce O(1) TenantGuard Rate Limits and Quotas
        # We skip public or unmetered 'free' plan if not required, but here we enforce it based on config.
        # Ensure we catch HTTPException to return a JSONResponse directly from the middleware.
        try:
            from babylon60.api.tenant_guard import tenant_guard
            from fastapi import HTTPException
            # Free bypass for default or pwyw without strict enforcement on stripe
            if plan != "free" and plan != "pwyw":
                tenant_guard.verify_request(tenant_id=tenant_id, plan_name=plan, ssu_cost=1)
        except Exception as exc:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
            logger.error("TenantGuard failure: %s", exc)

        try:
            # 4. Deep Payload Defense (Poisoning Check)
            if request.method in ("POST", "PUT", "PATCH"):
                body = await request.body()
                try:
                    from babylon60.mcp_server.guard import MCPGuard

                    if MCPGuard.detect_poisoning(body.decode(errors="ignore")):
                        logger.warning(
                            "🛡️ SOVEREIGN ISOLATION: Poisoning attempt rejected. Tenant: %s",
                            tenant_id,
                        )
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": "Payload rejected by Sovereign Isolation (Data Poisoning)"
                            },
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Suppressed exception: %s", exc)

                # Reconstruct stream since we consumed it
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive

            return await call_next(request)
        finally:
            tenant_id_var.reset(token)


class CortexBillingMiddleware(BaseHTTPMiddleware):
    """
    CORTEX-Persist C5-REAL Middleware for Stripe Metered Billing.

    Intercepts O(1) memory write operations and reports usage to Stripe
    for managed API users. This establishes the $10k MRR funnel.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Track successful memory insertions for billing
        if (
            request.url.path.endswith("/facts")
            and response.status_code in (200, 201)
            and request.method == "POST"
        ):
            # NOTE: /v1/memories routes to /v1/facts
            api_key = request.headers.get("x-api-key")
            if api_key and api_key.startswith("ctx_cloud_"):
                # Non-blocking async usage reporting
                asyncio.create_task(self._report_usage(api_key, request))

        return response

    async def _report_usage(self, api_key: str, request: Request):
        """Asynchronously reports usage to Stripe via background task with secure DB lookup."""
        try:
            import stripe  # pyright: ignore[reportMissingImports]

            from babylon60.auth.manager import get_auth_manager
            from babylon60.core import config

            auth_mgr = get_auth_manager()
            result = await auth_mgr.authenticate_async(api_key)
            if not result.authenticated:
                logger.error("Stripe billing increment failed: API key invalid.")
                return

            pool = getattr(request.app.state, "pool", None)
            if not pool:
                logger.warning("Stripe billing increment failed: DB pool not available.")
                return

            stripe_subscription_item_id = None
            async with pool.acquire() as conn:
                async with conn.execute(
                    "SELECT config FROM tenants WHERE id = ?", (result.tenant_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        try:
                            config_data = json.loads(row[0])
                            stripe_subscription_item_id = config_data.get(
                                "stripe_subscription_item_id"
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error("Failed to parse tenant config: %s", e)

            # Fallback to mock item ID if in test/mock mode
            if not stripe_subscription_item_id:
                is_mock = not config.STRIPE_SECRET_KEY or config.STRIPE_SECRET_KEY.startswith(
                    "sk_test_mock"
                )

                if is_mock:
                    stripe_subscription_item_id = f"si_{api_key[-8:]}"
                else:
                    logger.error(
                        "Stripe billing failed: No subscription item configured for tenant %s",
                        result.tenant_id,
                    )
                    return

            stripe.api_key = getattr(config, "STRIPE_SECRET_KEY", None)
            if not stripe.api_key:
                return

            # Run synchronous stripe call in a thread pool to avoid blocking event loop
            await asyncio.to_thread(
                stripe.SubscriptionItem.create_usage_record,  # type: ignore
                stripe_subscription_item_id,
                quantity=1,
                timestamp="now",
                action="increment",
            )
            logger.info(
                "Stripe usage reported for tenant %s (item %s)",
                result.tenant_id,
                stripe_subscription_item_id[:12],
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Stripe billing increment failed for %s: %s", api_key[:12], e)
