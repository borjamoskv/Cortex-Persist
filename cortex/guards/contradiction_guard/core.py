"""
Core detection logic for the Contradiction Guard.

Provides the primary functions to scan for contradictions, fetch decisions
from the database, and score candidate conflicts using multiple layers of
analysis including FTS5 overlap, project co-occurrence, and embedding similarity.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from cortex.database.core import connect_async_ctx
from cortex.utils.void_vec import cosine_similarity

from .models import ConflictCandidate, ConflictReport
from .nlp import (
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _jaccard,
    _tokenize,
)

logger = logging.getLogger("cortex.guards.contradiction.core")

MAX_CANDIDATES = 10
MIN_OVERLAP_SCORE = 0.10  # Jaccard threshold for keyword overlap

# Exported for testing compatibility
_embedding_cosine_similarity = cosine_similarity
EMBEDDING_BOOST_WEIGHT = 0.3  # Max boost from embedding similarity


def _classify_conflict(
    new_content: str,
    existing_content: str,
    new_tokens: set[str],
    existing_tokens: set[str],
    base_score: float,
) -> tuple[str, float]:
    """Classify the conflict type and apply appropriate score multipliers.

    Args:
        new_content: The newly proposed decision text.
        existing_content: The text of the existing decision.
        new_tokens: Set of tokens from the new decision.
        existing_tokens: Set of tokens from the existing decision.
        base_score: The initial conflict score (usually Jaccard similarity).

    Returns:
        A tuple containing the conflict type string and the adjusted score.
    """
    conflict_type = "keyword_overlap"

    if _detect_negation(new_content) or _detect_negation(existing_content):
        conflict_type = "negation"
        base_score *= 1.5

    if _detect_supersession(new_content) or _detect_supersession(existing_content):
        conflict_type = "version_supersede"
        base_score *= 1.2

    new_versions = _extract_versions(new_content)
    old_versions = _extract_versions(existing_content)
    if new_versions and old_versions and len(new_tokens & existing_tokens) > 5:
        conflict_type = "version_supersede"
        base_score *= 1.4

    return conflict_type, base_score


def _score_candidate(
    row: aiosqlite.Row | dict[str, Any],
    new_tokens: set[str],
    new_content: str,
    new_project: str,
    decrypt_fn: Callable[[str], str] | None,
    min_score: float,
    new_embedding: list[float] | None = None,
    existing_embedding: list[float] | None = None,
) -> ConflictCandidate | None:
    """Score a single database row against the new content.

    Args:
        row: The existing decision database record.
        new_tokens: Tokens from the new decision.
        new_content: Raw text of the new decision.
        new_project: The project context of the new decision.
        decrypt_fn: Optional decryption function for content.
        min_score: Minimum overlap score to consider as a conflict.
        new_embedding: Optional vector embedding of the new decision.
        existing_embedding: Optional vector embedding of the existing decision.

    Returns:
        A ConflictCandidate object if the score exceeds min_score, None otherwise.
    """
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


async def _fetch_decision_rows(
    conn: aiosqlite.Connection,
    new_tokens: set[str],
    new_project: str,
    *,
    use_fts: bool = True,
) -> list[aiosqlite.Row]:
    """Fetch candidate decision rows via FTS5 or full table scan.

    Args:
        conn: The active aiosqlite database connection.
        new_tokens: Tokens to search for if using FTS5.
        new_project: The project context to prioritize.
        use_fts: Whether to use Full-Text Search.

    Returns:
        A list of fetched database rows.
    """
    if not use_fts:
        cursor = await conn.execute(
            """
            SELECT id, project, content, created_at
            FROM facts
            WHERE fact_type = 'decision'
            ORDER BY CASE WHEN project = ? THEN 0 ELSE 1 END, id DESC
            LIMIT 400
            """,
            (new_project,),
        )
    else:
        fts_terms = " OR ".join(list(new_tokens)[:8])
        cursor = await conn.execute(
            """
            SELECT f.id, f.project, fts.content AS content, f.created_at
            FROM facts f
            JOIN facts_fts fts ON fts.rowid = f.id
            WHERE fts.facts_fts MATCH ?
              AND f.fact_type = 'decision'
            ORDER BY rank
            LIMIT 200
            """,
            (fts_terms,),
        )
    return list(await cursor.fetchall())


async def detect_contradictions(
    new_content: str,
    new_project: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: Callable[[str], str] | None = None,
    max_candidates: int = MAX_CANDIDATES,
    min_score: float = MIN_OVERLAP_SCORE,
) -> ConflictReport:
    """Scan existing decisions for potential contradictions with new content.

    Runs at store-time to enforce Epistemic Consistency (Axiom 20). Returns a
    report of potential conflicts so the system can disambiguate before persisting.

    Args:
        new_content: The new decision text.
        new_project: The project context for the decision.
        db_path: Path to the SQLite database.
        decrypt_fn: Optional function to decrypt existing decisions.
        max_candidates: Maximum number of conflict candidates to return.
        min_score: Minimum overlap score required to be flagged as a conflict.

    Returns:
        A ConflictReport containing zero or more prioritized candidates.
    """
    if _is_noise(new_content):
        return ConflictReport(new_content, new_project)

    new_tokens = _tokenize(new_content)
    if len(new_tokens) < 3:
        return ConflictReport(new_content, new_project)

    report = ConflictReport(new_content, new_project)

    async with connect_async_ctx(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        try:
            rows = await _fetch_decision_rows(
                conn,
                new_tokens,
                new_project,
                use_fts=not decrypt_fn,
            )
            candidates = [
                c
                for row in rows
                if (
                    c := _score_candidate(
                        row,
                        new_tokens,
                        new_content,
                        new_project,
                        decrypt_fn,
                        min_score,
                    )
                )
            ]
            candidates.sort(key=lambda x: -x.overlap_score)
            report.candidates = candidates[:max_candidates]
        except aiosqlite.OperationalError:
            logger.warning("Contradiction scan failed (DB error)", exc_info=True)

    return report
