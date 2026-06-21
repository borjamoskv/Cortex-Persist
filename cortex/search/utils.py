# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.crypto.aes import CortexEncrypter
from cortex.search.models import SearchResult

logger = logging.getLogger("cortex.search")

V6_PREFIX = CortexEncrypter.PREFIX


async def _has_fts5(conn: aiosqlite.Connection) -> bool:
    """Check if facts_fts virtual table exists."""
    try:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'"
        )
        return (await cursor.fetchone()) is not None
    except (aiosqlite.Error, sqlite3.Error):
        return False


def _has_fts5_sync(conn: sqlite3.Connection) -> bool:
    """Check if facts_fts virtual table exists (sync)."""
    try:
        cursor = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'")
        return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH syntax with token encapsulation.

    Prevents injection of FTS5 operators and ensures tokens are treated as literals.
    """
    if not query:
        return '""'

    # Escape quotes and remove potentially problematic characters
    cleaned_query = query.replace('"', '""').replace("'", "")

    tokens = cleaned_query.split()
    safe_tokens = []
    for token in tokens:
        # Wrap every token in double quotes to treat it as a literal
        # FTS5 allows "token" for literals. keywords (AND/OR) inside quotes are literals.
        if cleaned := token.strip():
            safe_tokens.append(f'"{cleaned}"')

    return " ".join(safe_tokens) if safe_tokens else '""'


def _row_to_result(row: Any, is_fts: bool = False) -> SearchResult:
    """Parse a database row into a SearchResult object with decryption logic.

    # Column order from _fts5_search / _like_search:
    #   0: f.id, 1: f.content, 2: f.project, 3: f.fact_type, 4: f.confidence,
    #   5: f.valid_from, 6: f.valid_until, 7: f.tags, 8: f.source, 9: f.metadata,
    #   10: f.created_at, 11: f.updated_at, 12: f.tx_id, 13: f.hash,
    #   14: f.consensus_score, 15: f.confidence_rank,
    #   16: bm25(facts_fts) AS rank  [FTS only]
    """
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    fact_id = row[0]
    tenant_id = "default"

    # Decrypt Content
    content = _decrypt_row_content(row[1], tenant_id, enc)

    # Process Tags (index 7)
    try:
        if isinstance(row[7], list):
            tags = row[7]
        else:
            tags = json.loads(row[7]) if len(row) > 7 and row[7] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    # Meta (index 9)
    meta = _parse_row_meta(row[9], tenant_id, enc) if len(row) > 9 else {}

    # Scoring - FTS has rank at index 16
    score = 0.5
    if is_fts and len(row) > 16:
        rank = row[16] if row[16] is not None else 0.0
        import math

        score = 1.0 / (1.0 + math.exp(rank / 10.0))

    # Ω₁₆: Consensus-aware confidence normalization natively mapping from columns 4, 14
    confidence = row[4] if len(row) > 4 else meta.get("confidence", "C3")
    c_score = row[14] if len(row) > 14 else meta.get("consensus_score", 1.0)
    if confidence in ("stated", "C3") and c_score >= 1.5:
        confidence = "verified"
    elif confidence in ("stated", "C3") and c_score <= 0.5:
        confidence = "disputed"

    meta["consensus_score"] = c_score

    # Ω₁₁: Hardened lineage (Issue #94) mapped directly
    tx_id = row[12] if len(row) > 12 else meta.get("tx_id")
    tx_hash = row[13] if len(row) > 13 else meta.get("hash")

    return SearchResult(
        fact_id=fact_id,
        content=content,
        project=row[2] if len(row) > 2 else "unknown",  # type: ignore[reportGeneralTypeIssues]
        fact_type=row[3] if len(row) > 3 else "fact",  # type: ignore[reportGeneralTypeIssues]
        confidence=confidence,  # type: ignore[reportGeneralTypeIssues]
        valid_from=row[5] if len(row) > 5 else "",  # type: ignore[reportGeneralTypeIssues]
        valid_until=row[6] if len(row) > 6 else None,  # type: ignore[reportGeneralTypeIssues]
        tags=tags,
        source=row[8] if len(row) > 8 else "unknown",  # type: ignore[reportGeneralTypeIssues]
        meta=meta,
        score=score,
        created_at=row[10] if len(row) > 10 else "",  # type: ignore[reportGeneralTypeIssues]
        updated_at=row[11] if len(row) > 11 else "",  # type: ignore[reportGeneralTypeIssues]
        tx_id=tx_id,  # type: ignore[reportGeneralTypeIssues]
        hash=tx_hash,  # type: ignore[reportGeneralTypeIssues]
    )


def _decrypt_row_content(content: str | None, tenant_id: str, enc: Any) -> str:
    """Helper to decrypt fact content if prefixed."""
    if content and str(content).startswith(V6_PREFIX):
        try:
            return enc.decrypt_str(content, tenant_id=tenant_id)
        except (ValueError, TypeError, OSError):
            logger.debug("Decryption failed for row content")
            # Fall back to content or empty string
    return content or ""


def _parse_row_meta(meta_raw: Any, tenant_id: str, enc: Any) -> dict[str, Any]:
    """Helper to parse and decrypt fact metadata."""
    if not meta_raw:
        return {}

    if isinstance(meta_raw, dict):
        return meta_raw

    meta_str = str(meta_raw)
    if meta_str.startswith(V6_PREFIX):
        try:
            return enc.decrypt_json(meta_raw, tenant_id=tenant_id) or {}
        except (ValueError, TypeError, OSError):
            return {}

    try:
        return json.loads(meta_str) if meta_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _rows_to_results(rows: list, is_fts: bool = False) -> list[SearchResult]:
    """Convert raw DB rows to SearchResult objects."""
    return [_row_to_result(row, is_fts) for row in rows]


def _parse_row_sync(row: Any, has_rank: bool) -> SearchResult:
    """Parse a database row into a SearchResult (sync).

    Sync Column order (minimal):
      0: id, 1: content, 2: project, 3: fact_type, 4: confidence, 5: source, 6: tags, 7: rank
    """
    try:
        tags = json.loads(row[6]) if row[6] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    if has_rank and len(row) > 7:
        # Normalize bm25 rank synchronously too
        import math

        rank = row[7] if row[7] is not None else 0.0
        score = 1.0 / (1.0 + math.exp(rank / 10.0))
    else:
        score = 0.5

    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()
    content = _decrypt_row_content(row[1], "default", enc)  # type: ignore[reportGeneralTypeIssues]

    return SearchResult(
        fact_id=row[0],  # type: ignore[reportGeneralTypeIssues]
        content=content,
        project=row[2],  # type: ignore[reportGeneralTypeIssues]
        fact_type=row[3],  # type: ignore[reportGeneralTypeIssues]
        confidence=row[4],  # type: ignore[reportGeneralTypeIssues]
        source=row[5],  # type: ignore[reportGeneralTypeIssues]
        tags=tags,
        score=score,
        valid_from="unknown",
        valid_until=None,
        created_at="unknown",
        updated_at="unknown",
    )
