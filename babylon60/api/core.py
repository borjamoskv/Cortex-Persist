# [C5-REAL] Exergy-Maximized
"""
REST API.

FastAPI server exposing the sovereign memory engine.
Main entry point for initialization, security middleware, and routing.
Optimized for high-concurrency memory lookups and secure agentic access.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import babylon60.api.state as api_state
from babylon60 import __version__, config
from babylon60.api.middleware import (
    ContentSizeLimitMiddleware,
    CortexBillingMiddleware,
    ImmuneMiddleware,
    RateLimitMiddleware,
    SecurityFraudMiddleware,
    SecurityHeadersMiddleware,
    TracingMiddleware,
)
from babylon60.auth import AuthManager
from babylon60.engine import CortexEngine
from babylon60.extensions.llm.quota import QuotaRejectedError
from babylon60.extensions.metering.middleware import MeteringMiddleware
from babylon60.extensions.swarm.manager import get_swarm_manager
from babylon60.extensions.timing import TimingTracker
from babylon60.mcp.knowledge_watcher import start_knowledge_daemon
from babylon60.routes import api_router
from babylon60.telemetry.metrics import MetricsMiddleware, metrics
from babylon60.utils.i18n import DEFAULT_LANGUAGE, get_trans

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
    from babylon60.database.pool import CortexConnectionPool
    from babylon60.engine import CortexEngine as AsyncCortexEngine

    db_path = config.DB_PATH
    logger.info("Lifespan: Initializing CORTEX with DB_PATH: %s", db_path)

    # 1. Schema & Migrations
    engine = CortexEngine(db_path)
    await engine.init_db()
    auth_manager = AuthManager()  # Use dynamic backend selection based on config
    await auth_manager.initialize()

    # Increment demo restart count for demo v0
    try:
        from babylon60.database.core import connect_async_ctx
        from babylon60.engine.mtk_sqlite_authorizer import mtk_active_token
        token_id = mtk_active_token.set("mtk_auth_demo")
        try:
            async with connect_async_ctx(db_path) as conn:
                await conn.execute("CREATE TABLE IF NOT EXISTS demo_system_state (key TEXT PRIMARY KEY, value TEXT)")
                await conn.execute("INSERT INTO demo_system_state (key, value) VALUES ('restarts', '1') ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)")
                await conn.commit()
        finally:
            mtk_active_token.reset(token_id)
        logger.info("Lifespan: Demo restart count incremented.")
    except Exception as e:
        logger.warning("Could not increment demo restarts: %s", e)

    from babylon60.ledger.billing_gateway import get_billing_gateway
    await get_billing_gateway().initialize()

    # 2. Connection Pool & Async Engine
    # IMPORTANT: The pool must allow writes (read_only=False) because AsyncCortexEngine uses it
    # for facts insertion.
    from babylon60.storage import StorageMode, get_storage_config, get_storage_mode

    if get_storage_mode() == StorageMode.POSTGRES:
        from babylon60.database.postgres_core import create_pool_async
        from babylon60.storage.postgres import PostgresBackend

        storage_config = get_storage_config()
        pg_dsn = storage_config["dsn"]

        # 2a. Bootstrap schema on Postgres
        pg_backend = PostgresBackend(pg_dsn)
        await pg_backend.connect()
        await pg_backend.close()

        # 2b. Initialize pool
        raw_pool = await create_pool_async(pg_dsn)
        from babylon60.database.postgres_adapter import PostgresPoolAdapter

        pool = PostgresPoolAdapter(raw_pool)
    else:
        pool = CortexConnectionPool(db_path, read_only=False)
        await pool.initialize()
    async_engine = AsyncCortexEngine(pool, db_path)

    app.state.swarm_manager = get_swarm_manager()

    # 3. Global Auth Registration
    import babylon60.auth

    babylon60.auth.manager._auth_manager = auth_manager  # type: ignore[reportAttributeAccessIssue]

    # 4. Temporal Tracking
    from babylon60.database.core import connect as db_connect

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

    # 6. Notification Bus - wire adapters from config
    from babylon60.extensions.notifications.setup import setup_notifications

    notification_bus = setup_notifications(config)
    api_state.notification_bus = notification_bus  # type: ignore[reportAttributeAccessIssue]

    # 7. V4 Singularity Daemons (Execution Plane Only)
    if config.DEPLOY_MODE != "cloud":
        from babylon60.swarm import start_swarm_daemon

        watcher = start_knowledge_daemon()
        swarm_daemon = start_swarm_daemon()
        app.state.watcher = watcher
        app.state.swarm_daemon = swarm_daemon
        logger.info("Lifespan: Sovereign Daemons initialized (Execution Plane).")
    else:
        app.state.watcher = None
        app.state.swarm_daemon = None
        logger.info("Lifespan: Daemons disabled in serverless mode (Control Plane).")

    try:
        yield
    finally:
        logger.info("Lifespan: Shutting down CORTEX endpoints.")
        await pool.close()
        await engine.close()
        await auth_manager.close()
        timing_conn.close()
        babylon60.auth.manager._auth_manager = None  # type: ignore[reportAttributeAccessIssue]
        api_state.engine = None
        api_state.auth_manager = None
        api_state.tracker = None
        api_state.notification_bus = None  # type: ignore[reportAttributeAccessIssue]


app = FastAPI(
    title="CORTEX - Sovereign Memory API",
    description="Local-first memory infrastructure for AI agents. "
    "Vector search, temporal facts, cryptographic ledger.",
    version=__version__,
    lifespan=lifespan,
    root_path="/api" if config.DEPLOY_MODE == "cloud" else "",
    docs_url="/docs" if not config.PROD else None,
    redoc_url="/redoc" if not config.PROD else None,
)

if not config.PROD:
    logger.info("MED-04: /docs and /redoc endpoints exposed (DEPLOY_MODE != cloud)")
app.state.swarm_manager = get_swarm_manager()


# ─── Internal Middleware ──────────────────────────────────────────────


# Middlewares imported from babylon60.middleware


# ─── Application Configuration ───────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityFraudMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(ImmuneMiddleware)
app.add_middleware(ContentSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=config.RATE_LIMIT, window=config.RATE_WINDOW)
app.add_middleware(MetricsMiddleware)
app.add_middleware(MeteringMiddleware)
app.add_middleware(CortexBillingMiddleware)


# ─── Exception Handlers ──────────────────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    # MED-01: Avoid leaking internal state in production
    if config.PROD:
        logger.warning("ValueError suppressed in PROD: %s", exc)
        return JSONResponse(status_code=422, content={"detail": "Invalid input."})
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    logger.error("Sovereign DB Error: %s", exc)

    # PULMONES: Map WAL locks to graceful 503 (Triangulación Antifrágil)
    if "database is locked" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "CORTEX_BUSY: Database is under heavy load. Retry in 2s."},
            headers={"Retry-After": "2"},
        )

    return JSONResponse(status_code=500, content={"detail": get_trans("error_internal_db", lang)})


@app.exception_handler(QuotaRejectedError)
async def quota_rejected_handler(request: Request, exc: QuotaRejectedError) -> JSONResponse:
    logger.error("Sovereign Quota Rejected: %s", exc)
    return JSONResponse(
        status_code=429,
        content={"detail": "CORTEX_OVERLOAD: Local PULMONES queue is full. Backoff required."},
        headers={"Retry-After": "5"},
    )


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
async def root_node(request: Request):
    from fastapi.responses import FileResponse

    # Content negotiation: serve HTML landing page to browsers
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        import os

        index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

    # Fallback to standard JSON health check for agents
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    return {
        "service": "cortex",
        "version": __version__,
        "status": get_trans("system_operational", lang),
        "description": get_trans("info_service_desc", lang),
    }


# ─── Backward Compatibility Redirects ───────────────────────────────


@app.api_route(
    "/v1/memories/{path:path}",
    methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    include_in_schema=False,
)
async def memory_redirect(path: str, request: Request):
    """Redirect legacy /v1/memories/* to /v1/facts/* (v5.1 consolidation)."""
    from fastapi.responses import RedirectResponse

    # Map the URL path
    new_url = str(request.url).replace("/v1/memories", "/v1/facts")
    logger.info("Redirecting legacy client: %s -> %s", request.url.path, new_url)
    return RedirectResponse(url=new_url, status_code=307)


@app.get("/api/v1/health", tags=["health"], include_in_schema=False)
@app.get("/health", tags=["health"])
async def health_check(request: Request) -> dict:
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    cortisol = 0.0
    growth = 0.0
    try:
        engine = getattr(request.app.state, "engine", None)
        if engine and hasattr(engine, "manager") and hasattr(engine.manager, "_endocrine"):
            cortisol = engine.manager._endocrine.cortisol_level
            growth = engine.manager._endocrine.neural_growth
    except (
        ValueError,
        KeyError,
        OSError,
        RuntimeError,
        AttributeError,
    ):
        pass

    # Health Index integration
    health_score = 0.0
    health_grade = "F"
    try:
        from babylon60.extensions.health import HealthCollector, HealthScorer

        db_path = ""
        engine = getattr(request.app.state, "engine", None)
        if engine:
            db_path = str(getattr(engine, "_db_path", ""))
        collector = HealthCollector(db_path=db_path)
        metrics_snap = collector.collect_all()
        hs = HealthScorer.score(metrics_snap)
        health_score = round(hs.score, 2)
        health_grade = hs.grade
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)

    return {
        "status": get_trans("system_healthy", lang),
        "engine": get_trans("engine_online", lang),
        "version": __version__,
        "cortisol": round(cortisol, 3),
        "neuroplasticity": round(growth, 3),
        "health_index": {
            "score": health_score,
            "grade": health_grade,
            "healthy": health_score >= 40.0,
        },
    }


@app.get("/metrics", tags=["health"])
async def get_metrics():
    from fastapi.responses import Response

    return Response(content=metrics.to_prometheus(), media_type="text/plain")


# ─── Router Inclusion ────────────────────────────────────────────────


app.include_router(api_router)  # pyright: ignore[reportArgumentType]

# V4 SSE Event Bus (Aether Matrix)
from babylon60.api import events as events_router

app.include_router(events_router.router)

# V5 LLM Proxy Middleware (Exergy Labyrinth)
from babylon60.routes import llm_proxy

app.include_router(llm_proxy.router)

# Extensions and third-party integrations

# Extension modules (opt-in)
if config.LANGBASE_API_KEY:
    from babylon60.routes.langbase import router as langbase_router

    app.include_router(langbase_router)
    logger.info("Langbase integration enabled")

if config.STRIPE_SECRET_KEY:
    from babylon60.routes.stripe import router as stripe_router

    app.include_router(stripe_router)
    logger.info("Stripe billing enabled")
