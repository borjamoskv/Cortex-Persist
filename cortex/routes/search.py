"""
CORTEX v4.0 - Search Router.
"""

from fastapi import APIRouter, Depends, Query, Request

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.models import SearchRequest, SearchResult

router = APIRouter(tags=["search"])


@router.post("/v1/search", response_model=list[SearchResult])
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[SearchResult]:
    """Semantic + Graph-RAG search across facts (scoped to tenant)."""
    results = await engine.search(
        query=req.query,
        top_k=req.k,
        project=auth.tenant_id or req.project,
        as_of=req.as_of,
        graph_depth=req.graph_depth,
        include_graph=req.include_graph,
    )
    return [
        SearchResult(
            fact_id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            score=r.score,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tx_id=r.tx_id,
            hash=r.hash,
            context=getattr(r, "context", None),
        )
        for r in results
    ]


@router.get("/v1/search", response_model=list[SearchResult])
async def search_facts_get(
    query: str = Query(..., max_length=1024),
    k: int = Query(5, ge=1, le=50),
    as_of: str | None = None,
    graph_depth: int = Query(0, ge=0, le=5),
    include_graph: bool = Query(False),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[SearchResult]:
    """Semantic + Graph-RAG search via GET (scoped to tenant)."""
    results = await engine.search(
        query=query,
        top_k=k,
        project=auth.tenant_id,
        as_of=as_of,
        graph_depth=graph_depth,
        include_graph=include_graph,
    )
    return [
        SearchResult(
            fact_id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            score=r.score,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tx_id=r.tx_id,
            hash=r.hash,
            context=getattr(r, "context", None),
        )
        for r in results
    ]
