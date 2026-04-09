"""CORTEX v5.1 - Facts Router.
Consolidated Memory-as-a-Service capabilities.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.requests import Request

from cortex.api.deps import get_async_engine, get_public_memory_service
from cortex.auth import require_permission
from cortex.engine.storage_guard import GuardViolation
from cortex.services.public_memory import PublicMemoryService, fact_like_to_dict
from cortex.types.models import (
    FactResponse,
    SearchRequest,
    SearchResult,
    StoreRequest,
    StoreResponse,
    VoteRequest,
    VoteResponse,
    VoteV2Request,
)
from cortex.utils.i18n import get_trans

if TYPE_CHECKING:
    from cortex.auth import AuthResult
    from cortex.engine import CortexEngine as AsyncCortexEngine
    from cortex.services.public_memory import PublicMemoryService


class BatchStoreFactRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=32_768)
    fact_type: str = Field("knowledge", validation_alias=AliasChoices("fact_type", "type"))
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    meta: dict[str, Any] | None = Field(
        None, validation_alias=AliasChoices("meta", "metadata")
    )
    parent_decision_id: int | None = None


class BatchStoreRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    facts: list[BatchStoreFactRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("facts", "memories"),
    )


router = APIRouter(tags=["facts"])
logger = logging.getLogger("uvicorn.error")


async def _store_fact_impl(
    *,
    project: str,
    content: str,
    tenant_id: str,
    service: PublicMemoryService,
    fact_type: str = "knowledge",
    tags: list[str] | None = None,
    source: str | None = None,
    meta: dict[str, Any] | None = None,
    parent_decision_id: int | None = None,
) -> StoreResponse:
    try:
        return await service.store(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=tags,
            source=source,
            meta=meta,
            parent_decision_id=parent_decision_id,
            tenant_id=tenant_id,
        )
    except (ValueError, GuardViolation) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Failed to store fact: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal server error while storing fact"
        ) from None


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> StoreResponse:
    """Store a fact (scoped to authenticated tenant)."""
    return await _store_fact_impl(
        project=req.project,
        content=req.content,
        tenant_id=auth.tenant_id,
        service=service,
        fact_type=req.fact_type,
        tags=req.tags,
        source=req.source,
        meta=req.meta,
    )


@router.post("/v1/facts/batch", response_model=dict)
async def batch_store(
    req: BatchStoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Batch store up to 100 facts in a single request."""
    payload = [
        {
            "project": fact.project,
            "content": fact.content,
            "tenant_id": auth.tenant_id,
            "fact_type": fact.fact_type,
            "tags": fact.tags,
            "source": fact.source,
            "meta": fact.meta or {},
            "parent_decision_id": fact.parent_decision_id,
        }
        for fact in req.facts
    ]

    try:
        fact_ids = await service.batch_store(payload)
    except (ValueError, GuardViolation) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Failed to batch store facts for tenant %s", auth.tenant_id)
        raise HTTPException(status_code=500, detail="Failed to batch store facts") from None

    return {
        "stored": len(fact_ids),
        "fact_ids": fact_ids,
        "errors": [],
        "total_requested": len(req.facts),
    }


@router.get("/v1/projects/{project}/facts", response_model=list[FactResponse])
async def recall_facts(
    project: str,
    request: Request,
    limit: int | None = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_deprecated: bool = Query(False),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    _ = request
    return await service.recall_project(
        project=project,
        tenant_id=auth.tenant_id,
        limit=limit,
        offset=offset,
        include_deprecated=include_deprecated,
    )


@router.get("/v1/facts", response_model=list[FactResponse])
async def list_all_facts(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[FactResponse]:
    # Retrieve all active facts across projects (scoped to tenant).
    return await service.list_active_facts(
        tenant_id=auth.tenant_id,
        limit=limit,
        offset=offset,
    )


@router.post("/v1/facts/search", response_model=list[SearchResult], include_in_schema=False)
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[SearchResult]:
    """Semantic search across all facts (scoped to tenant)."""
    return await service.search(
        query=req.query,
        top_k=req.k,
        project=req.project,
        tenant_id=auth.tenant_id,
        as_of=req.as_of,
        fact_type=req.fact_type,
        tags=req.tags,
        graph_depth=req.graph_depth,
        include_graph=req.include_graph,
        preserve_null_filters=True,
    )


@router.get("/v1/facts/{fact_id}/history", response_model=list[FactResponse])
async def get_fact_history(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[FactResponse]:
    """Retrieve version history for a specific fact."""
    try:
        return await service.fact_history(
            fact_id,
            tenant_id=auth.tenant_id,
        )
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Failed to fetch fact history: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch history") from e


@router.post("/v1/facts/{fact_id}/taint", response_model=dict)
async def propagate_taint(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Trigger Ω₁₃ taint propagation from a compromised/invalidated fact."""
    try:
        report = await engine.propagate_taint(fact_id, tenant_id=auth.tenant_id)
        return {
            "source_id": report.source_fact_id,
            "affected_count": report.affected_count,
            "changes": report.confidence_changes,
        }
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Taint propagation failed: %s", e)
        raise HTTPException(status_code=500, detail="Taint propagation failed") from None


@router.get("/v1/facts/verify", response_model=dict)
async def verify_ledger(
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Verify cryptographic integrity of the memory ledger."""
    try:
        report = await service.verify_ledger()
        return report
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
        fact_raw = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        if not fact_raw:
            raise HTTPException(
                status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
            )

        agent_id = auth.key_name or "api_agent"
        score = await engine.vote_v2(fact_id, agent_id, req.value)

        # Confidence is updated automatically by manager
        updated_fact_raw = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        updated_fact = fact_like_to_dict(updated_fact_raw) if updated_fact_raw else None

        return VoteResponse(
            fact_id=fact_id,
            agent=agent_id,
            vote=req.value,
            new_consensus_score=score,
            confidence=updated_fact.get("confidence") if updated_fact else "unknown",
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
        fact_raw = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        if not fact_raw:
            raise HTTPException(
                status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
            )

        score = await engine.vote_v2(
            fact_id=fact_id,
            agent_id=req.agent_id,
            value=req.vote,
        )

        # Re-fetch for updated confidence
        updated_fact_raw = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        updated_fact = fact_like_to_dict(updated_fact_raw) if updated_fact_raw else None

        return VoteResponse(
            fact_id=fact_id,
            agent=req.agent_id,
            vote=req.vote,
            new_consensus_score=score,
            confidence=updated_fact.get("confidence") if updated_fact else "unknown",
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

    votes = await engine.get_votes(fact_id, tenant_id=auth.tenant_id)

    return [
        {"agent": v["agent"], "vote": v["vote"], "timestamp": v.get("created_at")} for v in votes
    ]


@router.delete("/v1/facts/{fact_id}", response_model=dict)
async def deprecate_fact(
    fact_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    lang = request.headers.get("Accept-Language", "en")
    fact_raw = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact_raw:
        raise HTTPException(
            status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
        )
    fact = fact_like_to_dict(fact_raw)

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
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> FactResponse:
    """Get a single fact by ID."""
    fact = await service.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    return fact


@router.get("/v1/facts/{fact_id}/chain", response_model=list[dict])
async def get_causal_chain(
    fact_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[dict]:
    """Get the causal chain for a fact (up=ancestors, down=descendants)."""
    try:
        return await service.causal_chain(
            fact_id=fact_id,
            direction=direction,
            max_depth=max_depth,
            tenant_id=auth.tenant_id,
        )
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Causal chain query failed for #%d", fact_id)
        raise HTTPException(
            status_code=500,
            detail="Causal chain query failed",
        ) from None
