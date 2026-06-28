# [C5-REAL] Exergy-Maximized
import logging
import sqlite3
from collections.abc import Mapping
from typing import Any, Protocol, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.requests import Request

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.engine.flow.storage_guard import GuardViolation
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
Facts Router.
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


router = APIRouter(tags=["facts"])
logger = logging.getLogger("uvicorn.error")


class _FactLike(Protocol):
    """Minimal fact surface used by this router."""

    def to_dict(self) -> dict[str, Any]: ...


class _VotesEngine(Protocol):
    """Engine surface required for vote listing."""

    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict[str, Any]]: ...


class _TaintEngine(Protocol):
    """Engine surface required for taint propagation."""

    async def propagate_taint(self, fact_id: int, tenant_id: str) -> Any: ...


def _fact_data(fact: object) -> dict[str, Any]:
    """Normalize Fact-like objects to a mutable mapping for response shaping."""
    if isinstance(fact, Mapping):
        return dict(fact)

    to_dict = getattr(fact, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, Mapping):
            return dict(data)

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported fact payload type: {type(fact).__name__}",
    )


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
        return StoreResponse(fact_id=str(fact_id), project=req.project, message="Fact stored")
    except (ValueError, GuardViolation) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to store fact: %s", e)
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

    response: list[FactResponse] = []
    for fact in facts:
        fact_data = _fact_data(fact)
        response.append(
            FactResponse(
                id=str(fact_data["id"]),
                project=fact_data["project"],
                content=fact_data["content"],
                fact_type=fact_data["fact_type"],
                tags=fact_data["tags"],
                confidence=fact_data["confidence"],
                valid_from=fact_data["valid_from"],
                valid_until=fact_data["valid_until"],
                source=fact_data["source"],
                meta=fact_data["meta"],
                created_at=str(fact_data["created_at"]) if fact_data.get("created_at") else "",
                updated_at=str(fact_data["updated_at"]) if fact_data.get("updated_at") else "",
                tx_id=str(fact_data["tx_id"]) if fact_data.get("tx_id") is not None else None,
                hash=fact_data["hash"],
                consensus_score=fact_data.get("consensus_score", 1.0),
            )
        )
    return response


@router.get("/v1/facts", response_model=list[FactResponse])
async def list_all_facts(
    limit: int = Query(50, ge=1, le=1000),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[FactResponse]:
    # Retrieve all active facts across projects (scoped to tenant).
    facts = await engine.recall(project="", tenant_id=auth.tenant_id, limit=limit)

    response: list[FactResponse] = []
    for fact in facts:
        fact_data = _fact_data(fact)
        response.append(
            FactResponse(
                id=str(fact_data["id"]),
                project=fact_data["project"],
                content=fact_data["content"],
                fact_type=fact_data["fact_type"],
                tags=fact_data["tags"],
                confidence=fact_data.get("confidence") or "C3",
                valid_from=fact_data.get("valid_from"),
                valid_until=fact_data.get("valid_until"),
                source=fact_data.get("source"),
                meta=fact_data.get("meta"),
                created_at=str(fact_data.get("created_at", "")),
                updated_at=str(fact_data.get("updated_at", ""))
                or str(fact_data.get("created_at", "")),
                tx_id=str(fact_data.get("tx_id")) if fact_data.get("tx_id") is not None else None,
                hash=fact_data.get("hash"),
                consensus_score=float(fact_data.get("consensus_score", 1.0)),
            )
        )
    return response


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
            id=str(r.fact_id),
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            tags=r.tags,
            confidence=r.confidence,
            created_at=str(r.created_at) if r.created_at else "",
            updated_at=str(r.updated_at) if r.updated_at else "",
            hash=r.hash,
            consensus_score=r.score,
            tx_id=str(r.tx_id) if r.tx_id is not None else None,
        )
        for r in results
    ]


@router.get("/v1/facts/{fact_id}/history", response_model=list[FactResponse])
async def get_fact_history(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[FactResponse]:
    """Retrieve version history for a specific fact."""
    # Note: engine.history(project) returns audit trail for a PROJECT.
    # We need a per-FACT history. Since CORTEX versions via new facts linked to parents,
    # this is essentially a causal 'up' trace for that specific fact + any updates.
    # If using the 'updated_from' edge type.
    try:
        chain = await engine.get_causal_chain(
            fact_id=str(fact_id), direction="up", max_depth=50, tenant_id=auth.tenant_id
        )
        response: list[FactResponse] = []
        for fact in chain:
            fact_data = _fact_data(fact)
            response.append(
                FactResponse(
                    id=str(fact_data["id"]),
                    project=fact_data["project"],
                    content=fact_data["content"],
                    fact_type=fact_data["fact_type"],
                    tags=fact_data.get("tags", []),
                    confidence=fact_data.get("confidence", "C3"),
                    created_at=str(fact_data["created_at"]) if fact_data.get("created_at") else "",
                    updated_at=str(
                        fact_data.get("updated_at") or fact_data.get("created_at") or ""
                    ),
                    hash=fact_data.get("hash"),
                    tx_id=str(fact_data["tx_id"]) if fact_data.get("tx_id") is not None else None,
                )
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
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
        report = await cast(_TaintEngine, engine).propagate_taint(fact_id, tenant_id=auth.tenant_id)
        return {
            "source_id": report.source_fact_id,
            "affected_count": report.affected_count,
            "changes": report.confidence_changes,
        }
    except Exception as e:
        logger.error("Taint propagation failed: %s", e)
        raise HTTPException(status_code=500, detail="Taint propagation failed") from None


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
        score = await engine.vote_v2(fact_id, agent_id, req.value)

        # Confidence is updated automatically by manager
        updated_fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        updated_fact_data = _fact_data(updated_fact) if updated_fact else None

        return VoteResponse(
            fact_id=str(fact_id),
            agent=agent_id,
            vote=req.value,
            new_consensus_score=score,
            confidence=updated_fact_data["confidence"] if updated_fact_data else "unknown",
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

        score = await engine.vote_v2(
            fact_id=str(fact_id),
            agent=req.agent_id,
            value=req.vote,
        )

        # Re-fetch for updated confidence
        updated_fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
        updated_fact_data = _fact_data(updated_fact) if updated_fact else None

        return VoteResponse(
            fact_id=str(fact_id),
            agent=req.agent_id,
            vote=req.vote,
            new_consensus_score=score,
            confidence=updated_fact_data["confidence"] if updated_fact_data else "unknown",
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

    votes = await cast(_VotesEngine, engine).get_votes(fact_id, tenant_id=auth.tenant_id)

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
    fact = await engine.get_fact(fact_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(
            status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id)
        )
    fact_data = _fact_data(fact)
    if (
        fact_data.get("tenant_id", fact_data.get("project")) != auth.tenant_id
        and "tenant_id" in fact_data
    ):
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
    fact_data = _fact_data(fact)

    return FactResponse(
        id=str(fact_data["id"]),
        project=fact_data["project"],
        content=fact_data["content"],
        fact_type=fact_data["fact_type"],
        tags=fact_data["tags"],
        confidence=fact_data.get("confidence", "C3"),
        valid_from=fact_data.get("valid_from"),
        valid_until=fact_data.get("valid_until"),
        source=fact_data.get("source"),
        meta=fact_data.get("meta"),
        created_at=str(fact_data.get("created_at", "")),
        updated_at=str(fact_data.get("updated_at", "")),
        tx_id=str(fact_data.get("tx_id")) if fact_data.get("tx_id") is not None else None,
        hash=fact_data.get("hash"),
        consensus_score=float(fact_data.get("consensus_score", 1.0)),
    )


@router.get("/v1/facts/{fact_id}/chain", response_model=list[dict])
async def get_causal_chain(
    fact_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    tenant_id: str | None = Query(None, description="Scope query to specific tenant"),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Get the causal chain for a fact (up=ancestors, down=descendants)."""
    if tenant_id and tenant_id != auth.tenant_id and auth.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Tenant mismatch")
    effective_tenant = tenant_id or auth.tenant_id
    try:
        chain = await engine.get_causal_chain(
            fact_id=str(fact_id),
            direction=direction,
            max_depth=max_depth,
            tenant_id=effective_tenant,
        )
        chain_data = []
        for f in chain:
            fact_data = _fact_data(f)
            fact_data["causal_depth"] = fact_data.get("causal_depth", 0)
            chain_data.append(fact_data)
        return chain_data
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Causal chain query failed for #%d", fact_id)
        raise HTTPException(
            status_code=500,
            detail="Causal chain query failed",
        ) from None
