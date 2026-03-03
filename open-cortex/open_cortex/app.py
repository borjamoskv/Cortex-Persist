"""Open CORTEX — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from open_cortex.config import settings
from open_cortex.persistence import MemoryStore
from open_cortex.router import init_store, router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("open_cortex")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize the memory store on startup."""
    db_path = settings.database_url.replace("sqlite:///", "")
    store = MemoryStore(db_path=db_path)
    init_store(store)
    logger.info("Open CORTEX v0.1 initialized — %d memories", store.count(canonical_only=False))
    yield
    logger.info("Open CORTEX shutting down")


app = FastAPI(
    title="Open CORTEX",
    description="LLM-agnostic memory operating system with metamemory and reconsolidation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
