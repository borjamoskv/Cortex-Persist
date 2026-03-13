"""CORTEX v6.0 — Memories Router (Public API Surface).

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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine

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


class StoreMemoryRequest(BaseModel):
    """Request to store a memory."""

    project: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=32_768)
    type: str = Field("knowledge", description="knowledge, decision, error, etc.")
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str | None = Field(None, description="Origin (e.g., 'agent:my-bot')")
    metadata: dict[str, Any] | None = Field(None)
    parent_decision_id: int | None = Field(
        None,
        description="Causal parent fact ID for chain tracking",
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
    score: float | None = None


class SearchMemoryRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, max_length=1024, description="Natural language query")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    project: str | None = Field(None, description="Filter by project")
    tags: list[str] | None = Field(None, description="Filter by tags")
    as_of: str | None = Field(None, description="Temporal filter (ISO timestamp)")


class BatchStoreRequest(BaseModel):
    """Batch store request."""

    memories: list[StoreMemoryRequest] = Field(..., min_length=1, max_length=100)


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
    return [
        MemoryResponse(
            id=f["id"],
            project=f["project"],
            content=f["content"],
            type=f["fact_type"],
            tags=f["tags"],
            confidence=f.get("confidence", "C3"),
            created_at=f["created_at"],
            updated_at=f["updated_at"],
            hash=f.get("hash"),
        )
        for f in facts
    ]


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
    return [
        MemoryResponse(
            id=r.fact_id,
            project=r.project,
            content=r.content,
            type=r.fact_type,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
            hash=r.hash,
            score=r.score,
        )
        for r in results
    ]


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
        except (sqlite3.Error, ValueError, OSError) as e:
            errors.append({"index": i, "error": str(e)})

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

    return MemoryResponse(
        id=fact["id"],
        project=fact["project"],
        content=fact["content"],
        type=fact["fact_type"],
        tags=fact["tags"],
        confidence=fact.get("confidence", "C3"),
        created_at=fact["created_at"],
        updated_at=fact["updated_at"],
        hash=fact.get("hash"),
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

    success = await engine.deprecate(memory_id, reason="api_deleted")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")

    return {"id": memory_id, "status": "deleted"}


@router.get("/{memory_id}/chain", response_model=list[dict])
async def get_causal_chain(
    memory_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Get the causal chain for a memory (up=ancestors, down=descendants)."""
    try:
        chain = await engine.get_causal_chain(
            fact_id=memory_id,
            direction=direction,
            max_depth=max_depth,
        )
        return chain
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Causal chain query failed for #%d", memory_id)
        raise HTTPException(
            status_code=500,
            detail="Causal chain query failed",
        ) from None
