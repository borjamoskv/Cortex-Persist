"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.

Strategy (4-layer, O(N) bounded):
  1. FTS5 keyword overlap - fast, coarse.
  2. Project+topic co-occurrence - medium precision.
  3. Negation / supersession detection - high precision.
  4. Embedding cosine similarity - semantic precision (graceful degradation).

Returns a ConflictReport with scored candidates.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

import aiosqlite

from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from cortex.database.core import connect_async_ctx
from cortex.utils.void_vec import cosine_similarity
from .models import ConflictCandidate, ConflictReport
from .utils import (
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _jaccard,
    _tokenize,
)

logger = logging.getLogger("cortex.guards.contradiction")

MAX_CANDIDATES = 10
MIN_OVERLAP_SCORE = 0.10  # Jaccard threshold for keyword overlap


def _classify_conflict(
    new_content: str,
    existing_content: str,
    new_tokens: set[str],
    existing_tokens: set[str],
    base_score: float,
) -> tuple[str, float]:
    """Classify conflict type and apply score multipliers."""
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


_embedding_cosine_similarity = cosine_similarity


EMBEDDING_BOOST_WEIGHT = 0.3  # Max boost from embedding similarity


def _score_candidate(
    row: aiosqlite.Row,
    new_tokens: set[str],
    new_content: str,
    new_project: str,
    decrypt_fn: Callable | None,
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
    return await cursor.fetchall()  # type: ignore[type-error]


# ── Main detector ───────────────────────────────────────────────────
async def detect_contradictions(
    new_content: str,
    new_project: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: Callable | None = None,
    max_candidates: int = MAX_CANDIDATES,
    min_score: float = MIN_OVERLAP_SCORE,
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

    return report


# ── CLI-friendly batch scanner ──────────────────────────────────────
async def scan_all_contradictions(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: Callable | None = None,
    min_score: float = 0.45,
    limit: int = 50,
) -> list[tuple[ConflictCandidate, ConflictCandidate]]:
    """
    Batch scanner: find pairs of potentially contradicting decisions.
    """
    async with connect_async_ctx(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        try:
            cursor = await conn.execute(
                """
                SELECT id, project, content, created_at
                FROM facts
                WHERE fact_type = 'decision'
                ORDER BY id
                """
            )
            rows = await cursor.fetchall()
            decisions = _prepare_decisions(rows, decrypt_fn)  # type: ignore[type-error]

            by_project: dict[str, list[dict]] = defaultdict(list)
            for d in decisions:
                by_project[d["project"]].append(d)

            pairs: list[tuple[float, ConflictCandidate, ConflictCandidate]] = []
            seen_pairs: set[tuple[int, int]] = set()

            for _project, group in by_project.items():
                token_index = _build_token_index(group)
                for _token, indices in token_index.items():
                    _process_token_bucket(indices, group, seen_pairs, pairs, min_score)

            pairs.sort(key=lambda x: -x[0])
            return [(a, b) for _, a, b in pairs[:limit]]

        except aiosqlite.OperationalError:
            logger.warning("Batch contradiction scan failed", exc_info=True)
            return []


def _process_token_bucket(
    indices: list[int],
    group: list[dict],
    seen_pairs: set[tuple[int, int]],
    pairs: list[tuple[float, ConflictCandidate, ConflictCandidate]],
    min_score: float,
) -> None:
    """Compare all pairs within a token bucket."""
    if len(indices) < 2 or len(indices) > 50:
        return

    for i_pos in range(len(indices)):
        for j_pos in range(i_pos + 1, len(indices)):
            i, j = indices[i_pos], indices[j_pos]
            pair_key = (
                min(group[i]["id"], group[j]["id"]),
                max(group[i]["id"], group[j]["id"]),
            )
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            pair = _compare_decisions(group[i], group[j], min_score)
            if pair:
                pairs.append(pair)


def _compare_decisions(
    a: dict,
    b: dict,
    min_score: float,
) -> tuple[float, ConflictCandidate, ConflictCandidate] | None:
    """Score and classify a potential conflict between two decisions."""
    score = _jaccard(a["tokens"], b["tokens"])
    if score < min_score:
        return None

    # Batch-mode multipliers
    ctype = "keyword_overlap"
    if _detect_negation(a["content"]) or _detect_negation(b["content"]):
        ctype = "negation"
        score *= 1.3
    if _detect_supersession(a["content"]) or _detect_supersession(b["content"]):
        ctype = "version_supersede"
        score *= 1.2

    ca = ConflictCandidate(
        a["id"],
        a["project"],
        a["content"][:200],
        a["date"],
        min(score, 1.0),
        ctype,
    )
    cb = ConflictCandidate(
        b["id"],
        b["project"],
        b["content"][:200],
        b["date"],
        min(score, 1.0),
        ctype,
    )
    return (score, ca, cb)


def _prepare_decisions(rows: list, decrypt_fn: Callable | None) -> list[dict]:
    """Decrypt and tokenize raw database rows."""
    decisions = []
    for row in rows:
        content = _decrypt_content(row["content"], decrypt_fn)
        if not content or _is_noise(content):
            continue
        tokens = _tokenize(content)
        if len(tokens) < 3:
            continue
        decisions.append(
            {
                "id": row["id"],
                "project": row["project"],
                "content": content,
                "date": row["created_at"][:10],
                "tokens": tokens,
            }
        )
    return decisions


def _build_token_index(group: list[dict]) -> dict[str, list[int]]:
    """Build inverted index: token -> list of decision indices in the group."""
    token_index: dict[str, list[int]] = defaultdict(list)
    for idx, d in enumerate(group):
        top_tokens = sorted(d["tokens"], key=len, reverse=True)[:8]
        for token in top_tokens:
            token_index[token].append(idx)
    return token_index
