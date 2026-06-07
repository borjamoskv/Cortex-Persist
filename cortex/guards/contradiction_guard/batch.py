"""
Batch scanning logic for the Contradiction Guard.

Provides utilities for performing large-scale scans across the entire database
to identify pairs of conflicting decisions grouped by project.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from cortex.database.core import connect_async_ctx

from .models import ConflictCandidate
from .nlp import (
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _is_noise,
    _jaccard,
    _tokenize,
)

logger = logging.getLogger("cortex.guards.contradiction.batch")


def _compare_decisions(
    a: dict[str, Any],
    b: dict[str, Any],
    min_score: float,
) -> tuple[float, ConflictCandidate, ConflictCandidate] | None:
    """Score and classify a potential conflict between two decisions in batch mode.

    Args:
        a: Dictionary representing the first decision.
        b: Dictionary representing the second decision.
        min_score: Minimum overlap score to consider a conflict.

    Returns:
        A tuple of (score, Candidate A, Candidate B) if a conflict exists, None otherwise.
    """
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


def _process_token_bucket(
    indices: list[int],
    group: list[dict[str, Any]],
    seen_pairs: set[tuple[int, int]],
    pairs: list[tuple[float, ConflictCandidate, ConflictCandidate]],
    min_score: float,
) -> None:
    """Compare all pairs of decisions within a specific token bucket.

    Args:
        indices: List of indices pointing to items in the group.
        group: The list of decision dictionaries for a project.
        seen_pairs: Set to track already compared ID pairs to avoid duplication.
        pairs: List accumulating discovered conflict pairs.
        min_score: Threshold score for conflicts.
    """
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


def _prepare_decisions(
    rows: list[aiosqlite.Row | dict[str, Any]], decrypt_fn: Callable[[str], str] | None
) -> list[dict[str, Any]]:
    """Decrypt and tokenize raw database rows for batch processing.

    Args:
        rows: List of database rows or dictionaries representing decisions.
        decrypt_fn: Optional function to decrypt content.

    Returns:
        A list of processed dictionary objects with tokens extracted.
    """
    decisions: list[dict[str, Any]] = []
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


def _build_token_index(group: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Build an inverted index linking tokens to decision indices in the group.

    Args:
        group: List of processed decision dictionaries.

    Returns:
        A dictionary mapping top tokens to lists of decision indices.
    """
    token_index: dict[str, list[int]] = defaultdict(list)
    for idx, d in enumerate(group):
        top_tokens = sorted(d["tokens"], key=len, reverse=True)[:8]
        for token in top_tokens:
            token_index[token].append(idx)
    return token_index


async def scan_all_contradictions(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: Callable[[str], str] | None = None,
    min_score: float = 0.45,
    limit: int = 50,
) -> list[tuple[ConflictCandidate, ConflictCandidate]]:
    """Batch scanner to find pairs of potentially contradicting decisions.

    Args:
        db_path: Path to the SQLite database.
        decrypt_fn: Optional decryption function.
        min_score: Minimum overlap score to flag a conflict.
        limit: Maximum number of candidate pairs to return.

    Returns:
        A prioritized list of tuples, each containing two conflicting candidates.
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
            decisions = _prepare_decisions(list(rows), decrypt_fn)

            by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
