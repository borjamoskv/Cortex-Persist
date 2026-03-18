from __future__ import annotations

import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine.storage_guard import GuardViolation
from cortex.engine_async import AsyncCortexEngine
from cortex.types.models import (
    FactResponse,
    StoreRequest,
    StoreResponse,
    VoteRequest,
    VoteResponse,
    VoteV2Request,
)
from cortex.utils.i18n import get_trans

"""
CORTEX v5.1 - Facts Router.
Consolidated Memory-as-a-Service capabilities.
"""


class StoreMemoryRequest(BaseModel):
    project: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=32_768)
    type: str = Field("knowledge")
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    metadata: dict[str, Any] | None = None
    parent_decision_id: int | None = None


class BatchStoreRequest(BaseModel):
    memories: list[StoreMemoryRequest] = Field(..., min_length=1, max_length=100)


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    k: int = Field(5, ge=1, le=50)
    project: str | None = None
    tags: list[str] | None = None
    as_of: str | None = None


__all__ = [
    "batch_store",
    "cast_vote",
    "cast_vote_v2",
    "deprecate_fact",
    "get_causal_chain",
    "get_fact_by_id",
    "list_votes",
    "recall_facts",
    "search_facts",
    "store_fact",
    "verify_ledger",
]

router = APIRouter(tags=["facts"])
logger = logging.getLogger("uvicorn.error")


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> StoreResponse:
    """Store a fact (scoped to authenticated tenant)."""
    try:
        fact_id = await engine.store(
            project=req.project,
            content=req.content,
            tenant_id=auth.tenant_id,
            fact_type=req.fact_type,
            tags=req.tags,
            source=req.source,
            meta=req.meta,
        )
        return StoreResponse(fact_id=fact_id, project=req.project, message="Fact stored")
    except (ValueError, GuardViolation) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to store fact: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal server error while storing fact"
        ) from None


@router.post("/v1/facts/batch", response_model=dict)
async def batch_store(
    req: BatchStoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Batch store up to 100 facts in a single request."""
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
            logger.exception("Failed to batch store fact at index %d", i)
            errors.append({"index": i, "error": "Failed to store fact"})

    return {
        "stored": len(ids),
        "ids": ids,
        "errors": errors,
        "total_requested": len(req.memories),
    }


@router.get("/v1/projects/{project}/facts", response_model=list[FactResponse])
async def recall_facts(
    project: str,
    request: Request,
    limit: int | None = Query(None, ge=1, le=1000),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    _ = request
    facts = await engine.recall(project=project, tenant_id=auth.tenant_id, limit=limit)

    return [
        FactResponse(
            id=f["id"],
            project=f["project"],
            content=f["content"],
            fact_type=f["fact_type"],
            tags=f["tags"],
            confidence=f["confidence"],
            valid_from=f["valid_from"],
            valid_until=f["valid_until"],
            source=f["source"],  # type: ignore[reportCallIssue]
            meta=f["meta"],  # type: ignore[reportCallIssue]
            created_at=f["created_at"],
            updated_at=f["updated_at"],
            tx_id=f["tx_id"],
            hash=f["hash"],
            consensus_score=f.get("consensus_score", 1.0),
        )
        for f in facts
    ]


@router.post("/v1/facts/search", response_model=list[FactResponse])
async def search_facts(
    req: SearchMemoryRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[FactResponse]:
    """Semantic search across all facts (scoped to tenant)."""
    results = await engine.search(
        query=req.query,
        top_k=req.k,
        project=req.project,
        tenant_id=auth.tenant_id,
        as_of=req.as_of,
    )
    return [
        FactResponse(
            id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            tags=r.tags,
            confidence=r.confidence,
            created_at=r.created_at,
            updated_at=r.updated_at,
            hash=r.hash,
            consensus_score=r.score,
            tx_id=r.tx_id,
        )
        for r in results
    ]


@router.get("/v1/facts/verify", response_model=dict)
async def verify_ledger(
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


@router.post("/v1/facts/{fact_id}/vote", response_model=VoteResponse)
async def cast_vote(
    fact_id: int,
    req: VoteRequest,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a consensus vote (verify/dispute) on a fact."""
    lang = request.headers.get("Accept-Language", "en")
    try:
        fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        if not fact:
            raise HTTPException(
                status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
            )

        agent_id = auth.key_name or "api_agent"
        score = await engine.vote(fact_id, agent_id, req.value)

        # Confidence is updated automatically by manager
        updated_fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)

        return VoteResponse(
            fact_id=fact_id,
            agent=agent_id,
            vote=req.value,
            new_consensus_score=score,
            confidence=updated_fact["confidence"] if updated_fact else "unknown",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Unexpected error during voting for fact #%d", fact_id)
        raise HTTPException(
            status_code=500, detail=get_trans("error_internal_server", lang)
        ) from None


@router.post("/v1/facts/{fact_id}/vote-v2", response_model=VoteResponse)
async def cast_vote_v2(
    fact_id: int,
    req: VoteV2Request,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a reputation-weighted consensus vote (RWC)."""
    lang = request.headers.get("Accept-Language", "en")
    try:
        fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        if not fact:
            raise HTTPException(
                status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
            )

        score = await engine.vote(
            fact_id=fact_id,
            agent=req.agent_id,
            value=req.vote,
        )

        # Re-fetch for updated confidence
        updated_fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)

        return VoteResponse(
            fact_id=fact_id,
            agent=req.agent_id,
            vote=req.vote,
            new_consensus_score=score,
            confidence=updated_fact["confidence"] if updated_fact else "unknown",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("RWC Vote failed")
        raise HTTPException(
            status_code=500, detail=get_trans("error_internal_voting", lang)
        ) from None


@router.get("/v1/facts/{fact_id}/votes", response_model=list[dict])
async def list_votes(
    fact_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Retrieve all votes for a specific fact (Tenant Isolated)."""
    lang = request.headers.get("Accept-Language", "en")
    fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(
            status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
        )

    votes = await engine.get_votes(fact_id)

    return [{"agent": v[0], "vote": v[1], "tx_id": v[2]} for v in votes]


@router.delete("/v1/facts/{fact_id}", response_model=dict)
async def deprecate_fact(
    fact_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    lang = request.headers.get("Accept-Language", "en")
    fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(
            status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
        )

    if fact.get("tenant_id", fact.get("project")) != auth.tenant_id and "tenant_id" in fact:
        raise HTTPException(status_code=403, detail=get_trans("error_forbidden", lang))

    success = await engine.deprecate(fact_id, reason="api deprecated")
    if not success:
        raise HTTPException(status_code=500, detail=get_trans("error_deprecation_failed", lang))

    return {"message": f"Fact #{fact_id} deprecated", "success": True}


@router.get("/v1/facts/{fact_id}", response_model=FactResponse)
async def get_fact_by_id(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> FactResponse:
    """Get a single fact by ID."""
    fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")

    return FactResponse(
        id=fact["id"],
        project=fact["project"],
        content=fact["content"],
        fact_type=fact["fact_type"],
        tags=fact["tags"],
        confidence=fact.get("confidence", "C3"),
        valid_from=fact.get("valid_from"),
        valid_until=fact.get("valid_until"),
        source=fact.get("source"),
        meta=fact.get("meta"),
        created_at=fact["created_at"],
        updated_at=fact["updated_at"],
        tx_id=fact.get("tx_id"),
        hash=fact.get("hash"),
        consensus_score=fact.get("consensus_score", 1.0),
    )


@router.get("/v1/facts/{fact_id}/chain", response_model=list[dict])
async def get_causal_chain(
    fact_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Get the causal chain for a fact (up=ancestors, down=descendants)."""
    try:
        chain = await engine.get_causal_chain(
            fact_id=fact_id,
            direction=direction,
            max_depth=max_depth,
        )
        return chain
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Causal chain query failed for #%d", fact_id)
        raise HTTPException(
            status_code=500,
            detail="Causal chain query failed",
        ) from None
