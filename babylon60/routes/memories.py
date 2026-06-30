from decimal import Decimal
# [C5-REAL] Exergy-Maximized
"""Memories Router (Public API Surface).

Developer-friendly endpoints for the Memory-as-a-Service product.
Clean, intuitive naming that delegates to the existing CortexEngine.

Public API:
    POST   /v1/memories          → Store a memory
    GET    /v1/memories          → List memories (paginated)
    POST   /v1/memories/search   → Semantic search
    POST   /v1/memories/batch    → Batch store (up to plan limit)
    GET    /v1/memories/{id}     → Get single memory
    DELETE /v1/memories/{id}     → Delete memory
    GET    /v1/memories/verify   → Verify integrity (ledger check)
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from babylon60.api.deps import get_async_engine
from babylon60.auth import AuthResult, require_permission
from babylon60.engine import CortexEngine as AsyncCortexEngine

__all__ = [
    "batch_store",
    "delete_memory",
    "get_memory",
    "list_memories",
    "search_memories",
    "store_memory",
    "verify_memories",
]

router = APIRouter(prefix="/v1/memories", tags=["memories"])
logger = logging.getLogger(__name__)


# ─── Request / Response Models ───────────────────────────────────────


from babylon60.routes.facts import (
    BatchStoreRequest,
    SearchMemoryRequest,
    StoreMemoryRequest,
    _fact_data,
)


class MemoryResponse(BaseModel):
    """A single memory in the response."""

    id: int
    project: str
    content: str
    type: str
    tags: list[str]
    confidence: str = "C3"
    source: str | None = None
    parent_decision_id: int | None = None
    created_at: str
    updated_at: str
    hash: str | None = None
    score: Decimal | None = None


# ─── Endpoints ───────────────────────────────────────────────────────


@router.post("", response_model=dict)
async def store_memory(
    req: StoreMemoryRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Store a memory. Returns the memory ID and cryptographic hash."""
    try:
        fact_id = await engine.store(
            project=req.project,
            content=req.content,
            tenant_id=auth.tenant_id,
            fact_type=req.type,
            tags=req.tags,
            source=req.source,
            meta=req.metadata or {},
            parent_decision_id=req.parent_decision_id,
        )
        return {
            "id": fact_id,
            "project": req.project,
            "status": "stored",
        }
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Failed to store memory for tenant %s", auth.tenant_id)
        raise HTTPException(status_code=500, detail="Failed to store memory") from None


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    request: Request,
    project: str = Query(..., min_length=1, description="Project to list memories from"),
    limit: int = Query(50, ge=1, le=1000),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[MemoryResponse]:
    """List memories for a project (paginated)."""
    facts = await engine.recall(project=project, tenant_id=auth.tenant_id, limit=limit)
    response: list[MemoryResponse] = []
    for fact in facts:
        fact_data = _fact_data(fact)
        response.append(
            MemoryResponse(
                id=fact_data["id"],
                project=fact_data["project"],
                content=fact_data["content"],
                type=fact_data["fact_type"],
                tags=fact_data["tags"],
                confidence=fact_data.get("confidence", "C3"),
                created_at=fact_data["created_at"],
                updated_at=fact_data["updated_at"],
                hash=fact_data.get("hash"),
            )
        )
    return response


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    req: SearchMemoryRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[MemoryResponse]:
    """Semantic search across all memories (scoped to tenant)."""
    results = await engine.search(
        query=req.query,
        top_k=req.k,
        project=req.project,
        tenant_id=auth.tenant_id,
        as_of=req.as_of,
    )
    response: list[MemoryResponse] = []
    for result in results:
        response.append(
            MemoryResponse(
                id=result.fact_id,
                project=result.project,
                content=result.content,
                type=result.fact_type,
                tags=result.tags,
                created_at=result.created_at,
                updated_at=result.updated_at,
                hash=result.hash,
                score=result.score,
            )
        )
    return response


@router.post("/batch", response_model=dict)
async def batch_store(
    req: BatchStoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Batch store up to 100 memories in a single request."""
    ids: list[int] = []
    errors: list[dict] = []

    for i, mem in enumerate(req.memories):
        try:
            fact_id = await engine.store(
                project=mem.project,
                content=mem.content,
                tenant_id=auth.tenant_id,
                fact_type=mem.type,
                tags=mem.tags,
                source=mem.source,
                meta=mem.metadata or {},
                parent_decision_id=mem.parent_decision_id,
            )
            ids.append(fact_id)
        except (sqlite3.Error, ValueError, OSError):
            logger.exception("Failed to batch store memory at index %d", i)
            errors.append({"index": i, "error": "Failed to store memory"})

    return {
        "stored": len(ids),
        "ids": ids,
        "errors": errors,
        "total_requested": len(req.memories),
    }


@router.get("/verify", response_model=dict)
async def verify_memories(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Verify cryptographic integrity of the memory ledger."""
    try:
        report = await engine.verify_ledger()
        return {
            "valid": report["valid"],
            "violations": len(report.get("violations", [])),
            "transactions_checked": report.get("tx_checked", 0),
        }
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Ledger verification failed")
        raise HTTPException(status_code=500, detail="Integrity verification failed") from None


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> MemoryResponse:
    """Get a single memory by ID."""
    fact = await engine.get_fact(memory_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found")
    fact_data = _fact_data(fact)

    return MemoryResponse(
        id=fact_data["id"],
        project=fact_data["project"],
        content=fact_data["content"],
        type=fact_data["fact_type"],
        tags=fact_data["tags"],
        confidence=fact_data.get("confidence", "C3"),
        created_at=fact_data["created_at"],
        updated_at=fact_data["updated_at"],
        hash=fact_data.get("hash"),
    )


@router.delete("/{memory_id}", response_model=dict)
async def delete_memory(
    memory_id: int,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Delete (soft-deprecate) a memory."""
    fact = await engine.get_fact(memory_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found")

    success = await engine.deprecate(memory_id, reason="api_deleted", tenant_id=auth.tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")

    return {"id": memory_id, "status": "deleted"}


@router.get("/{memory_id}/chain", response_model=list[dict])
async def get_causal_chain(
    memory_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    tenant_id: str | None = Query(None, description="Scope query to specific tenant"),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Get the causal chain for a memory (up=ancestors, down=descendants)."""
    if tenant_id and tenant_id != auth.tenant_id and auth.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Tenant mismatch")
    effective_tenant = tenant_id or auth.tenant_id
    try:
        chain = await engine.get_causal_chain(
            fact_id=memory_id,
            direction=direction,
            max_depth=max_depth,
            tenant_id=effective_tenant,
        )
        return [_fact_data(fact) for fact in chain]
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Causal chain query failed for #%d", memory_id)
        raise HTTPException(
            status_code=500,
            detail="Causal chain query failed",
        ) from None
