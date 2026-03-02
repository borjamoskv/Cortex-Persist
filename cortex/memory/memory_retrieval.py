"""memory_retrieval — L2 Episodic Retrieval with Reciprocal Rank Fusion.

Extracted from CortexMemoryManager to satisfy the Landauer LOC barrier (≤500).
Pure retrieval logic: HDC + Dense recall + RRF fusion.
No state mutations. Always returns serializable dicts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.memory.manager import CortexMemoryManager
    from cortex.memory.models import CortexFactModel

__all__ = [
    "retrieve_episodic_context",
    "apply_rrf",
    "fact_to_dict",
]

logger = logging.getLogger("cortex.memory.retrieval")


def fact_to_dict(fact: CortexFactModel, rrf_score: float | None = None) -> dict[str, Any]:
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
    layer: str | None = None,
) -> list[CortexFactModel]:
    try:
        toxic_ids = await manager._hdc.get_toxic_ids(tenant_id=tenant_id, project_id=project_id)
        return await manager._hdc.recall_secure(
            tenant_id=tenant_id,
            project_id=project_id,
            query=query,
            limit=max_episodes * 2,
            inhibit_ids=toxic_ids,
            layer=layer,
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
    layer: str | None = None,
) -> list[CortexFactModel]:
    try:
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
        return await manager._l2.recall(query=query, limit=max_episodes)
    except (OSError, RuntimeError, ValueError) as e:
        logger.warning("Dense L2 recall failed: %s", e)
        return []


async def retrieve_episodic_context(
    manager: CortexMemoryManager,
    tenant_id: str,
    project_id: str,
    query: str | None,
    max_episodes: int,
    layer: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve and fuse facts from all available L2 layers.

    Strategy:
        1. HDC (Vector Alpha + Gamma Inhibition) — preferred
        2. Dense fallback (sqlite-vec) — if HDC unavailable
        3. RRF fusion — if both return results
    """
    if not query:
        return []

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

    if hdc_results and dense_results:
        return apply_rrf(dense_results, hdc_results, limit=max_episodes)
    elif hdc_results:
        return [fact_to_dict(f) for f in hdc_results[:max_episodes]]
    else:
        return [fact_to_dict(f) for f in dense_results[:max_episodes]]
