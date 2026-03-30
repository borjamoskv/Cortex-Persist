"""
CORTEX Terminal Snapshot Server — Lightweight standalone API.

Boots with minimal dependencies: only the CortexEngine + terminal snapshot route.
Bypasses the heavy main core.py and its extension imports.

Usage:
    uvicorn cortex.api.terminal_server:app --port 8000
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cortex.routes.terminal import router as terminal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.terminal_server")

app = FastAPI(
    title="CORTEX Terminal API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# --- CORS ---
ORIGINS = [
    "http://localhost:8080",
    "http://localhost:4321",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:4321",
    "https://borjamoskv.com",
    "https://www.borjamoskv.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# --- Lifespan: boot engine ---
@app.on_event("startup")
async def startup() -> None:
    """Boot a minimal CortexEngine for the terminal snapshot."""
    db_path = os.environ.get(
        "CORTEX_DB_PATH",
        os.path.expanduser("~/.cortex/cortex.db"),
    )
    try:
        from cortex.engine import CortexEngine

        engine = CortexEngine(db_path=db_path)
        await engine.initialize()
        app.state.engine = engine
        logger.info("CortexEngine booted: %s", db_path)
    except Exception:
        logger.warning("CortexEngine unavailable — snapshot will return nulls")
        app.state.engine = None


# --- Mount terminal route ---
app.include_router(terminal_router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "engine": app.state.engine is not None}
