"""
CORTEX v5.0 — Context Engine API Route.

Endpoints for ambient context inference, raw signals, and snapshot history.
"""

import logging
import time
import math
from collections import deque

from fastapi import APIRouter, Depends, Query, Request

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.context.collector import ContextCollector
from cortex.context.inference import ContextInference
from cortex.engine_async import AsyncCortexEngine
from cortex.types.models import (
    ContextSignalModel,
    ContextSnapshotResponse,
    ProjectScoreModel,
)

__all__ = ["infer_context", "list_signals", "context_history"]

router = APIRouter(prefix="/v1/context", tags=["context"])
logger = logging.getLogger("uvicorn.error")

# Global tracking for CORTEX v8 Axis 1 (Evaluation Layer)
_context_latencies: deque[float] = deque(maxlen=100)

def get_p95_context_latency() -> float | None:
    """Return the 95th percentile latency of the last 100 context inferences."""
    if not _context_latencies:
        return None
    sorted_latencies = sorted(_context_latencies)
    idx = int(math.ceil(len(sorted_latencies) * 0.95)) - 1
    return round(sorted_latencies[max(0, min(idx, len(sorted_latencies) - 1))], 1)


@router.get("/infer", response_model=ContextSnapshotResponse)
async def infer_context(
    request: Request,
    persist: bool = Query(True, description="Persist snapshot to DB"),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> ContextSnapshotResponse:
    """Run ambient context inference and return the current context snapshot."""
    from cortex import config
    
    start_time = time.monotonic()

    async with engine.session() as conn:
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

        inference = ContextInference(conn=conn if persist else None)
        if persist:
            result = await inference.infer_and_persist(signals)
        else:
            result = inference.infer(signals)

    elapsed_ms = (time.monotonic() - start_time) * 1000.0
    _context_latencies.append(elapsed_ms)

    return ContextSnapshotResponse(
        active_project=result.active_project,
        confidence=result.confidence,
        signals_used=result.signals_used,
        summary=result.summary,
        top_signals=[ContextSignalModel(**s.to_dict()) for s in result.top_signals],
        projects_ranked=[
            ProjectScoreModel(project=p, score=round(s, 4)) for p, s in result.projects_ranked
        ],
    )


@router.get("/signals", response_model=list[ContextSignalModel])
async def list_signals(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[ContextSignalModel]:
    """List raw ambient signals without running inference."""
    from cortex import config

    async with engine.session() as conn:
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

    return [ContextSignalModel(**s.to_dict()) for s in signals]


@router.get("/history", response_model=list[dict])
async def context_history(
    request: Request,
    limit: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Retrieve past context inference snapshots."""
    async with engine.session() as conn:
        inference = ContextInference(conn=conn)
        return await inference.get_history(limit=limit)
