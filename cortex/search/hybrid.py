"""
CORTEX v5.1 — Hybrid Search Engine.

Implements Reciprocal Rank Fusion (RRF) to unify semantic vector search
and full-text lexical search. Optimized for high-precision recall.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Final

import aiosqlite

from cortex.search.models import SearchResult
from cortex.search.text import text_search, text_search_sync
from cortex.search.vector import semantic_search, semantic_search_sync

__all__ = ['hybrid_search', 'hybrid_search_sync']

logger = logging.getLogger("cortex.search.hybrid")

# RRF_K constant governs the impact of low-rank results.
# Industry standard (Corpus-Scale) is 60.
RRF_K: Final[int] = 60


async def hybrid_search(
    conn: aiosqlite.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    project: str | None = None,
    as_of: str | None = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SearchResult]:
    """
    Sovereign Hybrid Search: Semantic + Text via RRF.
    Executes branch searches in parallel for minimal latency.
    """
    # 1. Dispatch branch searches concurrently
    # Over-fetch by 2x to ensure sufficient overlap for RRF
    fetch_limit = top_k * 2

    sem_task = semantic_search(conn, query_embedding, fetch_limit, project, as_of)
    txt_task = text_search(conn, query, project, limit=fetch_limit, as_of=as_of)

    try:
        sem_results, txt_results = await asyncio.gather(sem_task, txt_task)
    except Exception as exc:
        logger.error("Hybrid branch search failed: %s", exc)
        # Fallback to empty if both fail, or partial if one survives (non-gather approach would be needed)
        # But here we want atomicity or failure.
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
    project: str | None = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SearchResult]:
    """Hybrid search combining semantic + text via RRF (sync)."""
    fetch_limit = top_k * 2
    sem_results = semantic_search_sync(conn, query_embedding, fetch_limit, project)
    txt_results = text_search_sync(conn, query, project, limit=fetch_limit)

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

    return merged
