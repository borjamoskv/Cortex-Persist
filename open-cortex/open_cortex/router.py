"""Open CORTEX — FastAPI router with all 6 core endpoints.

Bronze: plan, recall, write, justify
Silver: + reconsolidate, audit
Gold:   + /metrics
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from open_cortex.config import settings
from open_cortex.metrics import (
    MetricsAggregator,
    TurnMetrics,
    compute_coverage,
    compute_ignored_memory_rate,
)
from open_cortex.models import (
    AuditResponse,
    Belief,
    JustifyRequest,
    JustifyResponse,
    Memory,
    PlanRequest,
    PlanResponse,
    Provenance,
    RecalledMemory,
    RecallMetamemory,
    RecallRequest,
    RecallResponse,
    ReconsolidateRequest,
    ReconsolidateResponse,
    WriteRequest,
    WriteResponse,
)
from open_cortex.persistence import MemoryStore

logger = logging.getLogger("open_cortex.router")

router = APIRouter(prefix="/v1", tags=["open-cortex"])

# ─── Singletons (initialized in app.py lifespan) ─────────────────────

_store: MemoryStore | None = None
_metrics = MetricsAggregator()


def init_store(store: MemoryStore) -> None:
    """Inject the persistence store."""
    global _store  # noqa: PLW0603
    _store = store


def get_store() -> MemoryStore:
    if _store is None:
        raise RuntimeError("Store not initialized — call init_store() first")
    return _store


# ─── 🥉 BRONZE TIER ──────────────────────────────────────────────────


@router.post("/plan", response_model=PlanResponse)
async def plan(req: PlanRequest) -> PlanResponse:
    """Step 1 — LLM generates a structured retrieval plan.

    The system validates JOL and may force recall.
    """
    # In a real implementation, the LLM generates this.
    # Here we return a template plan for the given query.
    response = PlanResponse(
        query_decomposition=[{"action": "recall", "filters": {}, "k": settings.default_k}],
        rationale=f"Plan for query: {req.query}",
    )

    # Metamemory enforcement: if JOL below threshold, force recall
    if response.metamemory.jol_expected < settings.jol_force_recall_threshold:
        response.metamemory.force_recall = True
        logger.info(
            "JOL %.2f < threshold %.2f → forcing recall",
            response.metamemory.jol_expected,
            settings.jol_force_recall_threshold,
        )

    return response


@router.post("/recall", response_model=RecallResponse)
async def recall(req: RecallRequest) -> RecallResponse:
    """Step 2 — Hybrid search (BM25 + ANN).

    Returns tagged memory chunks with confidence, freshness, source.
    """
    store = get_store()
    all_results: list[RecalledMemory] = []

    for query in req.queries:
        filters = query.filters
        memories = store.search_canonical(
            namespace=filters.get("namespace"),
            tags=filters.get("tags"),
            min_confidence=filters.get("min_confidence", 0.0),
            k=query.k,
            text_query=query.text,
        )

        for mem in memories:
            (mem.freshness.valid_from.timestamp() if mem.freshness.valid_from else 0)
            all_results.append(
                RecalledMemory(
                    memory_id=mem.id,
                    content=mem.content,
                    confidence=mem.belief.confidence,
                    freshness_days=0,  # TODO: compute from valid_from
                    source=mem.provenance.source.value,
                    relevance_score=mem.belief.confidence,  # Placeholder
                    is_canonical=mem.freshness.is_canonical,
                    tags=mem.tags,
                )
            )

    # Detect contradictions via edges
    contradiction = False
    for r in all_results:
        edges = store.get_edges(r.memory_id)
        for edge in edges:
            if edge.type.value == "contradicts":
                contradiction = True
                break

    return RecallResponse(
        plan_id=req.plan_id,
        results=all_results,
        metamemory=RecallMetamemory(
            fok_actual=max((r.relevance_score for r in all_results), default=0.0),
            coverage=len(all_results) / max(1, sum(q.k for q in req.queries)),
            contradiction_detected=contradiction,
        ),
    )


@router.post("/write", response_model=WriteResponse)
async def write(req: WriteRequest) -> WriteResponse:
    """Store a new memory with provenance and initial belief.confidence."""
    store = get_store()

    mem = Memory(
        content=req.content,
        tags=req.tags,
        namespace=req.namespace,
        provenance=Provenance(
            source=req.source,
            method=req.method,
            author=req.author,
            document_ref=req.document_ref,
        ),
        belief=Belief(confidence=req.confidence),
        relations=req.relations,
        meta=req.meta,
    )

    if req.valid_from:
        mem.freshness.valid_from = req.valid_from

    mem_id = store.write_memory(mem)

    return WriteResponse(
        id=mem_id,
        version=mem.version.v,
        is_canonical=True,
        belief=mem.belief,
        edges_created=len(req.relations),
    )


@router.post("/justify", response_model=JustifyResponse)
async def justify(req: JustifyRequest) -> JustifyResponse:
    """Step 3 — Record the LLM's memory usage report and compute metrics."""
    report = req.memory_use_report

    # Compute per-turn metrics
    used_ids = {c.memory_id for c in report.used_memories}
    recalled = [{"memory_id": c.memory_id, "confidence": 1.0} for c in report.used_memories]
    recalled += [{"memory_id": i.memory_id, "confidence": 0.5} for i in report.ignored_memories]

    coverage = compute_coverage(recalled, used_ids)
    ignored_rate = compute_ignored_memory_rate(
        total_recalled=len(recalled),
        total_used=len(report.used_memories),
    )

    turn = TurnMetrics(
        coverage=coverage,
        ignored_memory_rate=ignored_rate,
        plan_adherence=report.plan_adherence,
    )
    _metrics.record_turn(turn)

    # Warnings
    warnings: list[str] = []
    if coverage < 0.5:
        warnings.append("Low coverage — consider requesting additional evidence")
    if ignored_rate > 0.3:
        warnings.append("High ignored memory rate — retrieval may be returning noise")

    return JustifyResponse(
        plan_id=req.plan_id,
        metrics={
            "coverage": round(coverage, 4),
            "ignored_memory_rate": round(ignored_rate, 4),
            "plan_adherence": round(report.plan_adherence, 4),
        },
        warnings=warnings,
    )


# ─── 🥈 SILVER TIER ─────────────────────────────────────────────────


@router.post("/reconsolidate", response_model=ReconsolidateResponse)
async def reconsolidate(req: ReconsolidateRequest) -> ReconsolidateResponse:
    """Versioned truth update — creates new canonical, never deletes."""
    store = get_store()

    if req.confidence < settings.min_confidence_new:
        raise HTTPException(
            status_code=400,
            detail=f"Confidence {req.confidence} below minimum {settings.min_confidence_new}",
        )

    try:
        new_id, audit_id = store.reconsolidate(
            target_id=req.target_id,
            new_content=req.new_content,
            confidence=req.confidence,
            reason=req.reason,
            tags=req.tags or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ReconsolidateResponse(
        new_memory_id=new_id,
        superseded_id=req.target_id,
        old_canonical=False,
        new_canonical=True,
        audit_entry_id=audit_id,
    )


@router.get("/audit/{memory_id}", response_model=AuditResponse)
async def audit(memory_id: str) -> AuditResponse:
    """Full change history for a memory."""
    store = get_store()

    mem = store.get_memory(memory_id)
    if mem is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")

    history = store.get_audit_trail(memory_id)
    edges = store.get_edges(memory_id)
    chain = store.get_version_chain(memory_id)

    return AuditResponse(
        memory_id=memory_id,
        current_state={
            "is_canonical": mem.freshness.is_canonical,
            "confidence": mem.belief.confidence,
            "version": mem.version.v,
        },
        history=history,
        edges=edges,
        version_chain=chain,
    )


# ─── 🥇 GOLD TIER ───────────────────────────────────────────────────


@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Prometheus-compatible observability metrics."""
    store = get_store()
    return {
        "total_memories": store.count(canonical_only=False),
        "canonical_memories": store.count(canonical_only=True),
        "session_metrics": _metrics.summary(),
    }
