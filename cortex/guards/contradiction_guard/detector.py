"""
Main detection logic for contradiction guard.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import aiosqlite

from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from cortex.database.core import connect_async_ctx

from .models import ConflictReport
from .scoring import _score_candidate
from .utils import _is_noise, _tokenize

logger = logging.getLogger("cortex.guards.contradiction")

MAX_CANDIDATES = 10
MIN_OVERLAP_SCORE = 0.10  # Jaccard threshold for keyword overlap


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
        except (ValueError, TypeError, KeyError, AssertionError):
            # [Axiom Ω2] Teorema de Degradación de Robinson-Moskv
            # Blindaje de la ingesta de AST/Diffs. Fallo estructural imputable a Sensor Drift.
            logger.exception("☢️ Sensor Drift: Fallo crítico estructural (Apoptosis Local)")
            report.candidates = []

    return report
