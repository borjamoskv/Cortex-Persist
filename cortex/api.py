"""
CORTEX v5.1 — REST API.

FastAPI server exposing the sovereign memory engine.
Main entry point for initialization, security middleware, and routing.
Optimized for high-concurrency memory lookups and secure agentic access.
"""

import logging
import sqlite3
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex import __version__, api_state, config
from cortex.auth import AuthManager
from cortex.config import ALLOWED_ORIGINS, RATE_LIMIT, RATE_WINDOW
from cortex.engine import CortexEngine
from cortex.hive import router as hive_router
from cortex.i18n import DEFAULT_LANGUAGE, get_trans
from cortex.metrics import MetricsMiddleware, metrics
from cortex.routes import (
    admin as admin_router,
)
from cortex.routes import (
    agents as agents_router,
)
from cortex.routes import (
    ask as ask_router,
)
from cortex.routes import (
    context as context_router,
)
from cortex.routes import (
    daemon as daemon_router,
)
from cortex.routes import (
    dashboard as dashboard_router,
)
from cortex.routes import (
    facts as facts_router,
)
from cortex.routes import (
    gate as gate_router,
)
from cortex.routes import (
    graph as graph_router,
)
from cortex.routes import (
    ledger as ledger_router,
)
from cortex.routes import (
    mejoralo as mejoralo_router,
)
from cortex.routes import (
    missions as missions_router,
)
from cortex.routes import (
    search as search_router,
)
from cortex.routes import (
    timing as timing_router,
)
from cortex.routes import (
    tips as tips_router,
)
from cortex.routes import (
    translate as translate_router,
)
from cortex.timing import TimingTracker

__all__ = [
    "ContentSizeLimitMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "get_metrics",
    "health_check",
    "lifespan",
    "root_node",
    "sqlite_error_handler",
    "universal_error_handler",
    "value_error_handler",
]

logger = logging.getLogger("uvicorn.error")

# ─── Initialization ───────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize async connection pool, engine, auth, and timing on startup."""
    from cortex.connection_pool import CortexConnectionPool
    from cortex.engine_async import AsyncCortexEngine

    db_path = config.DB_PATH
    logger.info("Lifespan: Initializing CORTEX with DB_PATH: %s", db_path)

    # 1. Schema & Migrations
    engine = CortexEngine(db_path)
    await engine.init_db()
    auth_manager = AuthManager(db_path)

    # 2. Connection Pool & Async Engine
    pool = CortexConnectionPool(db_path)
    await pool.initialize()
    async_engine = AsyncCortexEngine(pool, db_path)

    # 3. Global Auth Registration
    import cortex.auth

    cortex.auth._auth_manager = auth_manager

    # 4. Temporal Tracking
    from cortex.db import connect as db_connect

    timing_conn = db_connect(db_path)
    tracker = TimingTracker(timing_conn)

    # 5. State Persistence
    app.state.pool = pool
    app.state.async_engine = async_engine
    app.state.engine = engine
    app.state.auth_manager = auth_manager
    app.state.tracker = tracker

    # Global backward compatibility
    api_state.engine = engine
    api_state.auth_manager = auth_manager
    api_state.tracker = tracker

    try:
        yield
    finally:
        logger.info("Lifespan: Shutting down CORTEX endpoints.")
        await pool.close()
        await engine.close()
        timing_conn.close()
        cortex.auth._auth_manager = None
        api_state.engine = None
        api_state.auth_manager = None
        api_state.tracker = None


app = FastAPI(
    title="CORTEX — Sovereign Memory API",
    description="Local-first memory infrastructure for AI agents. "
    "Vector search, temporal facts, cryptographic ledger.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if not config.PROD else None,
    redoc_url="/redoc" if not config.PROD else None,
)


# ─── Internal Middleware ──────────────────────────────────────────────


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Prevents large payload attacks by limiting request body size."""

    def __init__(self, app, max_size: int = 1_048_576):  # 1MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
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


# ─── Application Configuration ───────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(ContentSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=RATE_LIMIT, window=RATE_WINDOW)
app.add_middleware(MetricsMiddleware)


# ─── Exception Handlers ──────────────────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    logger.error("Sovereign DB Error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": get_trans("error_internal_db", lang)})


@app.exception_handler(Exception)
async def universal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    logger.error("Unhandled Sovereign Exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": get_trans("error_unexpected", lang)})


# ─── Global Routes ───────────────────────────────────────────────────


@app.get("/", tags=["health"])
async def root_node(request: Request) -> dict:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    return {
        "service": "cortex",
        "version": __version__,
        "status": get_trans("system_operational", lang),
        "description": get_trans("info_service_desc", lang),
    }


@app.get("/health", tags=["health"])
async def health_check(request: Request) -> dict:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    return {
        "status": get_trans("system_healthy", lang),
        "engine": get_trans("engine_online", lang),
        "version": __version__,
    }


@app.get("/metrics", tags=["health"])
async def get_metrics():
    from fastapi.responses import Response

    return Response(content=metrics.to_prometheus(), media_type="text/plain")


# ─── Router Inclusion ────────────────────────────────────────────────


app.include_router(facts_router.router)
app.include_router(search_router.router)
app.include_router(ask_router.router)
app.include_router(admin_router.router)
app.include_router(timing_router.router)
app.include_router(translate_router.router)
app.include_router(daemon_router.router)
app.include_router(dashboard_router.router)
app.include_router(agents_router.router)
app.include_router(graph_router.router)
app.include_router(ledger_router.router)
app.include_router(missions_router.router)
app.include_router(mejoralo_router.router)
app.include_router(gate_router.router)
app.include_router(context_router.router)
app.include_router(tips_router.router)
app.include_router(hive_router)

# Extension modules (opt-in)
if config.LANGBASE_API_KEY:
    from cortex.routes import langbase as langbase_router

    app.include_router(langbase_router.router)
    logger.info("Langbase integration enabled")

if config.STRIPE_SECRET_KEY:
    from cortex.routes import stripe as stripe_router

    app.include_router(stripe_router.router)
    logger.info("Stripe billing enabled")
