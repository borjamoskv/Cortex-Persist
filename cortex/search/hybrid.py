"""
CORTEX v5.1 — Hybrid Search Engine.

Implements Reciprocal Rank Fusion (RRF) to unify semantic vector search
and full-text lexical search. Optimized for high-precision recall.
"""

from __future__ import annotations

import asyncio
import logging
import math
import sqlite3
from datetime import datetime, timezone
from typing import Final

import aiosqlite

from cortex.search.causal_gap import (
    CausalGap,
    SearchCandidate,
    compute_candidate_score,
)
from cortex.search.models import SearchResult
from cortex.search.text import text_search, text_search_sync
from cortex.search.vector import semantic_search, semantic_search_sync

__all__ = ["hybrid_search", "hybrid_search_sync"]

logger = logging.getLogger("cortex.search.hybrid")

# RRF_K constant governs the impact of low-rank results.
# Industry standard (Corpus-Scale) is 60.
RRF_K: Final[int] = 60

# Temporal decay constant: λ=0.01 gives half-life ≈ 70 days
_DECAY_LAMBDA: Final[float] = 0.01


def _apply_temporal_decay(results: list[SearchResult], recency_weight: float) -> list[SearchResult]:
    """Apply exponential time decay to search results.

    Ω₁₃: A 2-year-old fact should not rank identically to today's.
    Uses exp(-λ * age_days) with configurable recency_weight blend.

    Final score = rrf_score * (1 - w) + recency_factor * w
    """
    now = datetime.now(timezone.utc)
    for r in results:
        try:
            # Parse created_at (ISO format from SQLite)
            created = datetime.fromisoformat(r.created_at.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (now - created).total_seconds() / 86400.0
        except (ValueError, TypeError, AttributeError):
            age_days = 0.0  # Unknown age = no penalty

        recency_factor = math.exp(-_DECAY_LAMBDA * max(age_days, 0.0))
        r.score = round(
            r.score * (1.0 - recency_weight) + recency_factor * recency_weight,
            6,
        )

    # Re-sort by updated scores
    results.sort(key=lambda r: r.score, reverse=True)
    return results


async def hybrid_search(
    conn: aiosqlite.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    tenant_id: str = "default",
    project: str | None = None,
    as_of: str | None = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    confidence: str | None = None,
    causal_gap: CausalGap | None = None,
    recency_weight: float = 0.1,
    **kwargs,
) -> list[SearchResult]:
    """
    Sovereign Hybrid Search: Semantic + Text via RRF.
    Executes branch searches in parallel for minimal latency.
    """
    # 1. Dispatch branch searches concurrently
    # Over-fetch by 2x to ensure sufficient overlap for RRF
    fetch_limit = top_k * 2

    sem_task = semantic_search(
        conn,
        query_embedding,
        top_k=fetch_limit,
        tenant_id=tenant_id,
        project=project,
        as_of=as_of,
        confidence=confidence,
    )
    txt_task = text_search(
        conn,
        query,
        tenant_id=tenant_id,
        project=project,
        limit=fetch_limit,
        as_of=as_of,
        confidence=confidence,
    )

    try:
        sem_results, txt_results = await asyncio.gather(sem_task, txt_task)
    except (sqlite3.Error, OSError, ValueError, RuntimeError) as exc:
        logger.error("Hybrid branch search failed: %s", exc)
        # Fallback to empty if both fail, or partial if one survives
        # (non-gather approach would be needed) But here we want atomicity or failure.
        return []

    # 2. Rank Fusion Logic (RRF)
    # Weights should ideally sum to 1.0 but we normalize them here
    total_w = vector_weight + text_weight
    w_vec = vector_weight / total_w
    w_txt = text_weight / total_w

    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SearchResult] = {}

    # Standardize Semantic Results
    for rank, res in enumerate(sem_results):
        score = w_vec / (RRF_K + rank + 1)
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + score
        result_map[res.fact_id] = res

    # Standardize Text Results
    for rank, res in enumerate(txt_results):
        score = w_txt / (RRF_K + rank + 1)
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + score
        if res.fact_id not in result_map:
            result_map[res.fact_id] = res

    # 3. Final Ranking & Selection
    # Sort by the aggregated RRF score
    sorted_ids = sorted(rrf_scores, key=lambda fid: rrf_scores[fid], reverse=True)[:top_k]

    merged: list[SearchResult] = []
    for fid in sorted_ids:
        r = result_map[fid]
        r.score = round(rrf_scores[fid], 6)
        merged.append(r)

    # Ω₁₃: Temporal decay — older facts naturally discounted
    if recency_weight > 0 and merged:
        merged = _apply_temporal_decay(merged, recency_weight)

    # Ω₁₃: Causal gap re-ranking — similarity alone is insufficient
    if causal_gap is not None and merged:
        merged = _rerank_by_causal_gap(merged, causal_gap)

    logger.debug(
        "Hybrid search executed. query='%s' results=%d top_score=%.4f",
        query[:30],
        len(merged),
        merged[0].score if merged else 0.0,
    )

    return merged


def hybrid_search_sync(
    conn: sqlite3.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    tenant_id: str = "default",
    project: str | None = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    causal_gap: CausalGap | None = None,
    recency_weight: float = 0.1,
) -> list[SearchResult]:
    """Hybrid search combining semantic + text via RRF (sync)."""
    fetch_limit = top_k * 2
    sem_results = semantic_search_sync(
        conn, query_embedding, fetch_limit, tenant_id=tenant_id, project=project
    )
    txt_results = text_search_sync(
        conn, query, tenant_id=tenant_id, project=project, limit=fetch_limit
    )

    total_w = vector_weight + text_weight
    w_vec = vector_weight / total_w
    w_txt = text_weight / total_w

    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SearchResult] = {}

    for rank, res in enumerate(sem_results):
        score = w_vec / (RRF_K + rank + 1)
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + score
        result_map[res.fact_id] = res

    for rank, res in enumerate(txt_results):
        score = w_txt / (RRF_K + rank + 1)
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + score
        if res.fact_id not in result_map:
            result_map[res.fact_id] = res

    sorted_ids = sorted(rrf_scores, key=lambda fid: rrf_scores[fid], reverse=True)[:top_k]
    merged: list[SearchResult] = []
    for fid in sorted_ids:
        r = result_map[fid]
        r.score = round(rrf_scores[fid], 6)
        merged.append(r)

    # Ω₁₃: Temporal decay
    if recency_weight > 0 and merged:
        merged = _apply_temporal_decay(merged, recency_weight)

    # Ω₁₃: Causal gap re-ranking
    if causal_gap is not None and merged:
        merged = _rerank_by_causal_gap(merged, causal_gap)

    return merged


def _rerank_by_causal_gap(
    results: list[SearchResult],
    gap: CausalGap,
) -> list[SearchResult]:
    """Re-rank results by causal gap reduction, not mere similarity.

    Ω₁₃: causal_gap_reduction_required_for_search_success = true
    """
    missing = gap.missing_evidence.lower()
    candidates: list[tuple[SearchResult, float]] = []

    for rank, r in enumerate(results):
        content_lower = r.content.lower()
        # Evidence match: word overlap with missing_evidence
        missing_words = set(missing.split())
        content_words = set(content_lower.split())
        overlap = len(missing_words & content_words)
        evidence_score = min(overlap / max(len(missing_words), 1), 1.0)

        sc = SearchCandidate(
            doc_id=str(r.fact_id),
            semantic_score=r.score,
            evidence_match_score=evidence_score,
            confidence_gain_score=gap.expected_confidence_gain,
            novelty_score=1.0 / (rank + 1),  # Higher rank = lower novelty
        )
        final = compute_candidate_score(sc)
        r.causal_gap_score = round(final, 6)
        candidates.append((r, final))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates]
