# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6.0 — Cross-Encoder Reranking Layer.

Resolves Ghost RETRIEVAL-RERANK-001: zero contextual reranking across
all retrieval surfaces. Injects a cross-encoder evaluation between
rank-fusion and context delivery.

Architecture:
    Query + Documents → Cross-Encoder → relevance_score per doc → top_n

The cross-encoder evaluates the *direct semantic relationship* between
query and each document — unlike embedding distance (symmetric) or BM25
(lexical), this produces a contextual relevance judgment.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~22MB, ~50ms for 10 docs)
Fallback: passthrough (no reranking) if model fails to load.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Sequence, TypeVar

__all__ = [
    "rerank_search_results",
    "rerank_dicts",
    "CrossEncoderReranker",
]

logger = logging.getLogger("cortex.search.reranker")

# Default model — small, fast, excellent for passage reranking
_DEFAULT_MODEL = os.environ.get(
    "CORTEX_RERANK_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

T = TypeVar("T")


class CrossEncoderReranker:
    """Singleton cross-encoder reranker.

    Lazy-loads the model on first use to avoid startup cost.
    Thread-safe via Python's GIL for the predict call.
    """

    _instance: CrossEncoderReranker | None = None
    _model: Any = None
    _model_name: str = _DEFAULT_MODEL
    _available: bool = False

    def __new__(cls) -> CrossEncoderReranker:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_loaded(self) -> bool:
        """Lazy-load the cross-encoder model. Returns True if available."""
        if self._model is not None:
            return self._available

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
            self._available = True
            logger.info(
                "✅ Cross-encoder reranker loaded: %s",
                self._model_name,
            )
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning(
                "Cross-encoder unavailable (degrading to passthrough): %s", e
            )
            self._available = False

        return self._available

    def rank(
        self,
        query: str,
        documents: list[str],
    ) -> list[tuple[int, float]]:
        """Score and rank documents against query.

        Returns:
            List of (original_index, relevance_score) sorted by score descending.
        """
        if not documents:
            return []

        if not self._ensure_loaded():
            # Passthrough: return original order with uniform scores
            return [(i, 1.0 / (i + 1)) for i in range(len(documents))]

        # Cross-encoder expects list of [query, document] pairs
        pairs = [[query, doc] for doc in documents]

        try:
            scores = self._model.predict(pairs)
            # Create (index, score) and sort by score descending
            indexed_scores = list(enumerate(float(s) for s in scores))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            return indexed_scores
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Cross-encoder prediction failed: %s", e)
            return [(i, 1.0 / (i + 1)) for i in range(len(documents))]

    @property
    def available(self) -> bool:
        """Check if the reranker is available (loads model if needed)."""
        return self._ensure_loaded()

    @property
    def model_name(self) -> str:
        return self._model_name


# ─── Module-level singleton ─────────────────────────────────────────

_reranker = CrossEncoderReranker()


# ─── Public API: SearchResult reranking ──────────────────────────────


def rerank_search_results(
    query: str,
    results: Sequence[Any],
    top_n: int | None = None,
    content_attr: str = "content",
) -> list[Any]:
    """Rerank SearchResult objects using the cross-encoder.

    Args:
        query: The user's search query.
        results: List of SearchResult (or any object with a content attribute).
        top_n: Number of top results to return. None = return all, reranked.
        content_attr: Attribute name to extract text from each result.

    Returns:
        Reranked list of results, truncated to top_n.
    """
    if not results:
        return list(results)

    documents = [getattr(r, content_attr, str(r)) for r in results]
    ranked = _reranker.rank(query, documents)

    if top_n is not None:
        ranked = ranked[:top_n]

    reranked = []
    for original_idx, score in ranked:
        result = results[original_idx]
        # Update score to reflect reranking relevance
        if hasattr(result, "score"):
            result.score = score
        reranked.append(result)

    logger.debug(
        "Reranked %d → %d results for query='%s'",
        len(results),
        len(reranked),
        query[:40],
    )
    return reranked


# ─── Public API: Dict reranking (for memory_retrieval.py) ────────────


def rerank_dicts(
    query: str,
    results: list[dict[str, Any]],
    top_n: int | None = None,
    content_key: str = "content",
) -> list[dict[str, Any]]:
    """Rerank dicts (from episodic retrieval) using the cross-encoder.

    Args:
        query: The user's search query.
        results: List of fact dicts with a 'content' key.
        top_n: Number of top results to return. None = return all, reranked.
        content_key: Key to extract text from each dict.

    Returns:
        Reranked list of dicts, truncated to top_n.
    """
    if not results:
        return results

    documents = [r.get(content_key, "") for r in results]
    ranked = _reranker.rank(query, documents)

    if top_n is not None:
        ranked = ranked[:top_n]

    reranked = []
    for original_idx, score in ranked:
        entry = results[original_idx].copy()
        entry["score"] = score
        entry["_reranked"] = True
        reranked.append(entry)

    return reranked
