"""memory_retrieval — L2 Episodic Retrieval with Reciprocal Rank Fusion.

Extracted from CortexMemoryManager to satisfy the Landauer LOC barrier (≤500).
Pure retrieval logic: HDC + Dense recall + RRF fusion.
No state mutations. Always returns serializable dicts.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.memory.manager import CortexMemoryManager
    from cortex.memory.models import CortexFactModel

__all__ = [
    "KnowledgeGapException",
    "retrieve_episodic_context",
    "apply_rrf",
    "fact_to_dict",
]

logger = logging.getLogger("cortex.memory.retrieval")


class KnowledgeGapException(Exception):
    """Raised when Metamemory FOK evaluates retrieval potential as too low to proceed."""

    pass


def fact_to_dict(fact: CortexFactModel, rrf_score: Optional[float] = None) -> dict[str, Any]:
    """Convert a fact model to a context-ready dict."""
    return {
        "id": fact.id,
        "content": fact.content,
        "timestamp": fact.timestamp,
        "score": rrf_score if rrf_score is not None else getattr(fact, "_recall_score", 0.0),
        "metadata": fact.metadata,
    }


def apply_rrf(
    dense: list[CortexFactModel],
    hdc: list[CortexFactModel],
    limit: int = 3,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Apply Reciprocal Rank Fusion to merge dense and HDC results.

    O(N) over ranked lists — produces a single sorted output.
    """
    scores: dict[str, float] = {}
    facts: dict[str, CortexFactModel] = {}

    for rank, fact in enumerate(dense):
        scores[fact.id] = scores.get(fact.id, 0.0) + 1.0 / (k + rank + 1)
        facts[fact.id] = fact

    for rank, fact in enumerate(hdc):
        scores[fact.id] = scores.get(fact.id, 0.0) + 1.0 / (k + rank + 1)
        facts[fact.id] = fact

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [fact_to_dict(facts[fid], rrf_score=scores[fid]) for fid in sorted_ids[:limit]]


async def _fetch_hdc_results(
    manager: CortexMemoryManager,
    tenant_id: str,
    project_id: str,
    query: str,
    max_episodes: int,
    layer: Optional[str] = None,
) -> list[CortexFactModel]:
    try:
        toxic_ids = await manager._hdc.get_toxic_ids(tenant_id=tenant_id, project_id=project_id)  # type: ignore[reportOptionalMemberAccess]
        return await manager._hdc.recall_secure(  # type: ignore[reportOptionalMemberAccess]
            tenant_id=tenant_id,
            project_id=project_id,
            query=query,
            limit=max_episodes * 2,
            inhibit_ids=toxic_ids,
            layer=layer,  # type: ignore[reportCallIssue]
        )
    except (OSError, RuntimeError, ValueError) as e:
        logger.warning("HDC recall failed: %s", e)
        return []


async def _fetch_dense_results(
    manager: CortexMemoryManager,
    tenant_id: str,
    project_id: str,
    query: str,
    max_episodes: int,
    layer: Optional[str] = None,
) -> list[CortexFactModel]:
    try:
        # [VECTOR-2] ZERO-FRICTION HOLOGRAPHIC RECALL
        if getattr(manager, "_hologram", None) is not None and manager._hologram.is_ready:  # type: ignore
            # O(1) in-RAM lookup without I/O
            logger.debug("🌌 Querying Holographic Memory (RAM-resident)")
            return await manager._hologram.recall_holographic(  # type: ignore
                query=query,
                limit=max_episodes,
                tenant_id=tenant_id,
                project_id=project_id,
                layer=layer,
            )

        if hasattr(manager._l2, "recall_secure"):
            if manager._dynamic_space:
                return await manager._dynamic_space.recall_and_pulse(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    query=query,
                    limit=max_episodes,
                    layer=layer,
                )
            return await manager._l2.recall_secure(
                tenant_id=tenant_id,
                project_id=project_id,
                query=query,
                limit=max_episodes,
                layer=layer,
            )
        return await manager._l2.recall(query=query, limit=max_episodes, tenant_id=tenant_id)
    except (OSError, RuntimeError, ValueError) as e:
        logger.warning("Dense L2 recall failed: %s", e)
        return []


def apply_retrieval_schemas(manager: CortexMemoryManager, query: str) -> str:
    """Apply schema retrieval biases to modify search focus top-down."""
    schema_engine = getattr(manager, "_schema_engine", None)
    if not schema_engine:
        return query

    schema = schema_engine.match_schema(query)
    if schema:
        logger.debug("Applied Schema '%s' to retrieval query", schema.name)
        return schema_engine.apply_retrieval_schema(schema, query)
    return query


async def retrieve_episodic_context(
    manager: CortexMemoryManager,
    tenant_id: str,
    project_id: str,
    query: Optional[str],
    max_episodes: int,
    layer: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieve and fuse facts from all available L2 layers.

    Strategy:
        1. HDC (Vector Alpha + Gamma Inhibition) — preferred
        2. Dense fallback (sqlite-vec) — if HDC unavailable
        3. RRF fusion — if both return results
    """
    if not query:
        return []

    # 0. Apply Top-Down Retrieval Schema Bias
    query = apply_retrieval_schemas(manager, query)

    dense_results: list[CortexFactModel] = []
    hdc_results: list[CortexFactModel] = []

    if manager._hdc:
        hdc_results = await _fetch_hdc_results(
            manager, tenant_id, project_id, query, max_episodes, layer=layer
        )

    if not hdc_results and manager._l2:
        dense_results = await _fetch_dense_results(
            manager, tenant_id, project_id, query, max_episodes, layer=layer
        )

    # 4. Metamemory Gate: Abort if FOK is too low (Knowledge Gap)
    candidate_engrams = hdc_results if hdc_results else dense_results
    if hasattr(manager, "metamemory") and candidate_engrams:
        query_embedding = await manager._encoder.encode(query)
        judgment = manager.metamemory.judge_fok(query_embedding, candidate_engrams)
        threshold = getattr(manager.metamemory, "_fok_threshold", 0.3)
        if judgment.fok_score < threshold:
            logger.warning(
                "Retrieval aborted: KnowledgeGapException (FOK=%.2f < %.2f)",
                judgment.fok_score,
                threshold,
            )
            raise KnowledgeGapException(
                f"Metamemory FOK too low ({judgment.fok_score:.2f}). "
                "Aborting retrieval to prevent local hallucination."
            )

    # 5. Fuse results
    if hdc_results and dense_results:
        results = apply_rrf(dense_results, hdc_results, limit=max_episodes)
    elif hdc_results:
        results = [fact_to_dict(f) for f in hdc_results[:max_episodes]]
    else:
        results = [fact_to_dict(f) for f in dense_results[:max_episodes]]

    # 6. Hebbian Ranking Boost (STDP edge weights)
    results = _apply_hebbian_boost(manager, results)
    return results


def _apply_hebbian_boost(
    manager: CortexMemoryManager,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Boost retrieval scores using STDP edge co-activation weights.

    Facts connected by strong Hebbian edges get their scores amplified,
    causing co-activated knowledge to surface higher in rankings.
    O(N²) over result set — bounded by max_episodes (~3-10).
    """
    stdp = getattr(manager, "_stdp_engine", None)
    if stdp is None or len(results) < 2:
        return results

    # Accumulate Hebbian boost per fact from pairwise edge weights
    boosted = []
    for item in results:
        fid = item.get("id", "")
        hebb_boost = 0.0
        for other in results:
            oid = other.get("id", "")
            if fid != oid:
                w = stdp.get_edge_weight(str(fid), str(oid))
                hebb_boost += w
        # Apply: original score + 20% Hebbian signal
        new_score = item.get("score", 0.0) + 0.2 * hebb_boost
        boosted.append({**item, "score": new_score})

    boosted.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return boosted
