"""
Scoring functions for Contradiction Guard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import aiosqlite

from cortex.guards.contradiction_guard.models import ConflictCandidate
from cortex.guards.contradiction_guard.nlp import (
    _classify_conflict,
    _decrypt_content,
    _is_noise,
    _jaccard,
    _tokenize,
)
from cortex.utils.void_vec import cosine_similarity

_embedding_cosine_similarity = cosine_similarity


EMBEDDING_BOOST_WEIGHT = 0.3  # Max boost from embedding similarity


def _score_candidate(
    row: aiosqlite.Row,
    new_tokens: set[str],
    new_content: str,
    new_project: str,
    decrypt_fn: Callable[..., Any] | None,
    min_score: float,
    new_embedding: list[float] | None = None,
    existing_embedding: list[float] | None = None,
) -> ConflictCandidate | None:
    """Score a single row against new content. Returns None if below threshold."""
    content = _decrypt_content(row["content"], decrypt_fn)
    if not content or _is_noise(content):
        return None

    existing_tokens = _tokenize(content)
    score = _jaccard(new_tokens, existing_tokens)

    # Project boost: same project = 1.3x
    if row["project"] == new_project:
        score *= 1.3

    # Layer 4: Embedding cosine similarity boost (Ω₁₃ upgrade)
    cosine_sim = cosine_similarity(new_embedding, existing_embedding)
    if cosine_sim > 0.5:
        score += EMBEDDING_BOOST_WEIGHT * cosine_sim

    if score < min_score:
        return None

    conflict_type, score = _classify_conflict(
        new_content,
        content,
        new_tokens,
        existing_tokens,
        score,
    )

    # If embedding similarity is very high but Jaccard is low, flag as semantic conflict
    if cosine_sim > 0.8 and _jaccard(new_tokens, existing_tokens) < 0.2:
        conflict_type = "semantic_similarity"

    return ConflictCandidate(
        fact_id=row["id"],
        project=row["project"],
        content=content[:300],
        date=row["created_at"][:10],
        overlap_score=min(score, 1.0),
        conflict_type=conflict_type,
    )
