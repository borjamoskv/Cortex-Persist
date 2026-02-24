"""
CORTEX v5.1 — REST API.

FastAPI server exposing the sovereign memory engine.
Main entry point for initialization, security middleware, and routing.
Optimized for high-concurrency memory lookups and secure agentic access.
"""

import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cortex import __version__, config; import cortex.api.state as api_state
from cortex.auth import AuthManager

from cortex.engine import CortexEngine
from cortex.hive.main import router as hive_router
from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans
from cortex.telemetry.metrics import MetricsMiddleware, metrics
from cortex.api.middleware import (
    ContentSizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityFraudMiddleware,
    SecurityHeadersMiddleware,
)
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
    telemetry as telemetry_router,
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
    "SecurityFraudMiddleware",
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
    from cortex.database.pool import CortexConnectionPool
    from cortex.engine_async import AsyncCortexEngine

    db_path = config.DB_PATH
    logger.info("Lifespan: Initializing CORTEX with DB_PATH: %s", db_path)

    # 1. Schema & Migrations
    engine = CortexEngine(db_path)
    await engine.init_db()
    auth_manager = AuthManager()  # Use dynamic backend selection based on config
    await auth_manager.initialize()

    # 2. Connection Pool & Async Engine
    # IMPORTANT: The pool must allow writes (read_only=False) because AsyncCortexEngine uses it
    # for facts insertion.
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()
    async_engine = AsyncCortexEngine(pool, db_path)

    # 3. Global Auth Registration
    import cortex.auth

    cortex.auth._auth_manager = auth_manager

    # 4. Temporal Tracking
    from cortex.database.core import connect as db_connect

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

    # 6. Notification Bus — wire adapters from config
    from cortex.notifications.setup import setup_notifications

    notification_bus = setup_notifications(config)
    api_state.notification_bus = notification_bus

    try:
        yield
    finally:
        logger.info("Lifespan: Shutting down CORTEX endpoints.")
        await pool.close()
        await engine.close()
        await auth_manager.close()
        timing_conn.close()
        cortex.auth._auth_manager = None
        api_state.engine = None
        api_state.auth_manager = None
        api_state.tracker = None
        api_state.notification_bus = None


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


# Middlewares imported from cortex.middleware


# ─── Application Configuration ───────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityFraudMiddleware)
app.add_middleware(ContentSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=config.RATE_LIMIT, window=config.RATE_WINDOW)
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
    logger.error(
        "Sovereign Critical Error | Path: %s | Method: %s | Exc: %s",
        request.url.path,
        request.method,
        exc,
        exc_info=True,
    )
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
app.include_router(telemetry_router.router)
app.include_router(hive_router)

# Gateway — Universal Intelligence Entry Point
from cortex.gateway.adapters import (  # noqa: E402
    rest_router as gateway_rest_router,
)
from cortex.gateway.adapters import (  # noqa: E402
    telegram_router as gateway_telegram_router,
)

app.include_router(gateway_rest_router)
app.include_router(gateway_telegram_router)

# Extension modules (opt-in)
if config.LANGBASE_API_KEY:
    from cortex.routes import langbase as langbase_router

    app.include_router(langbase_router.router)
    logger.info("Langbase integration enabled")

if config.STRIPE_SECRET_KEY:
    from cortex.routes import stripe as stripe_router

    app.include_router(stripe_router.router)
    logger.info("Stripe billing enabled")
