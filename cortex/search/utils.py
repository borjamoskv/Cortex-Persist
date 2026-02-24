# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Search utilities."""

import json
import sqlite3

import aiosqlite

from typing import Any
from cortex.search.models import SearchResult
from cortex.crypto.aes import CortexEncrypter

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


def _row_to_result(row: tuple, is_fts: bool = False) -> SearchResult:
    """Parse a database row into a SearchResult object with decryption logic.

    Column order from _fts5_search / _like_search:
      0: f.id, 1: f.content, 2: f.project, 3: f.fact_type, 4: f.confidence,
      5: f.valid_from, 6: f.valid_until, 7: f.tags, 8: f.source, 9: f.meta,
      10: f.created_at, 11: f.updated_at, 12: f.tx_id, 13: t.hash,
      14: bm25(facts_fts) AS rank  [FTS only]
    """
    from cortex.crypto import get_default_encrypter
    enc = get_default_encrypter()

    fact_id = row[0]
    tenant_id = "default"

    # Decrypt Content
    content = _decrypt_row_content(row[1], tenant_id, enc)

    # Process Tags (index 7)
    try:
        tags = json.loads(row[7]) if row[7] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    # Meta (index 9)
    meta = _parse_row_meta(row[9], tenant_id, enc)

    # Scoring — FTS has rank at index 14
    score = 0.0
    if is_fts and len(row) > 14:
        score = row[14] if row[14] is not None else 0.0

    return SearchResult(
        fact_id=fact_id,
        content=content,
        project=row[2],
        fact_type=row[3],
        confidence=row[4],
        valid_from=row[5] or "",
        valid_until=row[6],
        tags=tags,
        source=row[8],
        meta=meta,
        score=score,
        created_at=row[10] or "",
        updated_at=row[11] or "",
        tx_id=row[12],
        hash=row[13],
    )


def _decrypt_row_content(content: str | None, tenant_id: str, enc: Any) -> str:
    """Helper to decrypt fact content if prefixed."""
    if content and str(content).startswith(V6_PREFIX):
        try:
            return enc.decrypt_str(content, tenant_id=tenant_id)
        except Exception:
            pass
    return content or ""


def _parse_row_meta(meta_raw: Any, tenant_id: str, enc: Any) -> dict[str, Any]:
    """Helper to parse and decrypt fact metadata."""
    if not meta_raw:
        return {}

    meta_str = str(meta_raw)
    if meta_str.startswith(V6_PREFIX):
        try:
            return enc.decrypt_json(meta_raw, tenant_id=tenant_id) or {}
        except Exception:
            return {}

    try:
        return json.loads(meta_str) if meta_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _rows_to_results(rows: list, is_fts: bool = False) -> list[SearchResult]:
    """Convert raw DB rows to SearchResult objects."""
    return [_row_to_result(row, is_fts) for row in rows]


def _parse_row_sync(row: tuple, has_rank: bool) -> SearchResult:
    """Parse a database row into a SearchResult (sync)."""
    try:
        tags = json.loads(row[6]) if row[6] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    if has_rank and len(row) > 7:
        score = -row[7] if row[7] else 0.5
    else:
        score = 0.5

    from cortex.crypto import get_default_encrypter
    enc = get_default_encrypter()

    content = row[1]
    if content and str(content).startswith(V6_PREFIX):
        try:
            content = enc.decrypt_str(content)
        except Exception:
            pass

    return SearchResult(
        fact_id=row[0],
        content=content,
        project=row[2],
        fact_type=row[3],
        confidence=row[4],
        source=row[5],
        tags=tags,
        score=score,
        valid_from="unknown",  # Sync rows often have fewer columns
        valid_until=None,
        created_at="unknown",
        updated_at="unknown",
    )
