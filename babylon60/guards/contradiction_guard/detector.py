from decimal import Decimal
# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import aiosqlite

from babylon60.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from babylon60.database.core import connect_async_ctx
from babylon60.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from babylon60.guards.contradiction_guard.utils import (
    _classify_conflict,
    _decrypt_content,
    _is_noise,
    _jaccard,
    _tokenize,
)
from babylon60.utils.void_vec import cosine_similarity

logger = logging.getLogger("babylon60.guards.contradiction.detector")

MAX_CANDIDATES = 10
MIN_OVERLAP_SCORE = 0.10  # Jaccard threshold for keyword overlap
EMBEDDING_BOOST_WEIGHT = 0.3  # Max boost from embedding similarity

_embedding_cosine_similarity = cosine_similarity


def _score_candidate(
    row: aiosqlite.Row,
    new_tokens: set[str],
    new_content: str,
    new_project: str,
    decrypt_fn: Callable[[str], str] | None,
    min_score: Decimal,
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


async def _fetch_decision_rows(
    conn: aiosqlite.Connection,
    new_tokens: set[str],
    new_project: str,
    *,
    use_fts: bool = True,
) -> list[aiosqlite.Row]:
    """Fetch candidate rows via FTS5 or full scan."""
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
    min_score: Decimal = MIN_OVERLAP_SCORE,
) -> ConflictReport:
    """
    Scan existing decisions for potential contradictions with new_content.
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
        except (ValueError, TypeError, KeyError, AssertionError):
            # [Axiom Ω2] Robinson-Moskv Degradation Theorem
            logger.exception("☢️ Sensor Drift: Critical structural failure (Local Apoptosis)")
            report.candidates = []

    return report
