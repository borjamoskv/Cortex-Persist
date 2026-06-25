# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

from legacy_research.memory.temporal import build_temporal_filter_params
from legacy_research.search.models import SearchResult
from legacy_research.search.utils import (
    _has_fts5,
    _has_fts5_sync,
    _parse_row_sync,
    _rows_to_results,
    _sanitize_fts_query,
)
from legacy_research.storage import StorageMode, get_storage_mode

__all__ = ["text_search", "text_search_sync"]

logger = logging.getLogger("cortex.search.text")

_PROJECT_FILTER = " AND f.project = ?"


async def text_search(
    conn: Any,
    query: str,
    tenant_id: str = "default",
    project: str | None = None,
    fact_type: str | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
    as_of: str | None = None,
    confidence: str | None = None,
    **kwargs,
) -> list[SearchResult]:
    """Perform text search (async)."""
    if get_storage_mode() == StorageMode.POSTGRES:
        try:
            rows = await _postgres_text_search(
                conn, query, tenant_id, project, fact_type, tags, limit, as_of, confidence
            )
            return _rows_to_results(rows, is_fts=False)
        except Exception as e:
            logger.error("Postgres text search failed: %s", e)
            return []

    use_fts = await _has_fts5(conn)
    try:
        if use_fts:
            rows = await _fts5_search(
                conn, query, tenant_id, project, fact_type, tags, limit, as_of, confidence
            )
        else:
            rows = await _like_search(
                conn, query, tenant_id, project, fact_type, tags, limit, as_of, confidence
            )
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error("Text search failed: %s", e)
        return []
    return _rows_to_results(rows, is_fts=use_fts)


async def _postgres_text_search(
    conn: Any,
    query: str,
    tenant_id: str,
    project: str | None,
    fact_type: str | None,
    tags: list[str] | None,
    limit: int,
    as_of: str | None,
    confidence: str | None,
) -> list:
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.meta as metadata,
               f.created_at, f.updated_at, f.tx_id, t.hash,
               f.consensus_score, 1.0::double precision as confidence_rank
        FROM facts f
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE f.tenant_id = $1 AND f.content ILIKE $2
    """
    params: list = [tenant_id, f"%{query}%"]
    param_idx = 3

    if as_of:
        sql += f" AND f.valid_from <= ${param_idx} AND (f.valid_until IS NULL OR f.valid_until > ${param_idx}) AND f.is_tombstoned = FALSE"
        params.append(as_of)
        param_idx += 1
    else:
        sql += " AND f.valid_until IS NULL AND f.is_tombstoned = FALSE"

    if project:
        sql += f" AND f.project = ${param_idx}"
        params.append(project)
        param_idx += 1

    if fact_type:
        sql += f" AND f.fact_type = ${param_idx}"
        params.append(fact_type)
        param_idx += 1

    if tags:
        for tag in tags:
            sql += f" AND f.tags ILIKE ${param_idx}"
            params.append(f"%{tag}%")
            param_idx += 1

    if confidence:
        sql += f" AND f.confidence >= ${param_idx}"
        params.append(confidence)
        param_idx += 1

    sql += f" ORDER BY f.updated_at DESC LIMIT ${param_idx}"
    params.append(limit)

    if hasattr(conn, "fetch"):
        return await conn.fetch(sql, *params)
    elif hasattr(conn, "acquire"):
        async with conn.acquire() as real_conn:
            return await real_conn.fetch(sql, *params)
    else:
        raise TypeError(
            f"PostgreSQL connection object has no fetch or acquire method: {type(conn)}"
        )


async def _fts5_search(
    conn: aiosqlite.Connection,
    query: str,
    tenant_id: str,
    project: str | None,
    fact_type: str | None,
    tags: list[str] | None,
    limit: int,
    as_of: str | None,
    confidence: str | None,
) -> list:
    fts_query = _sanitize_fts_query(query)
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.metadata,
               f.created_at, f.updated_at, f.tx_id, f.hash,
               f.consensus_score, f.confidence_rank, bm25(facts_fts) AS rank
        FROM facts_fts fts JOIN facts f ON f.id = fts.rowid
        WHERE f.tenant_id = ? AND fts.content MATCH ?
    """
    params: list = [tenant_id, fts_query]
    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += " AND f.valid_until IS NULL"
    if project:
        sql += _PROJECT_FILTER
        params.append(project)
    if fact_type:
        sql += " AND f.fact_type = ?"
        params.append(fact_type)
    if tags:
        for tag in tags:
            sql += " AND json_extract(f.tags, '$') LIKE ?"
            params.append(f"%{tag}%")
    if confidence:
        sql += " AND f.confidence >= ?"
        params.append(confidence)
    sql += " ORDER BY rank ASC LIMIT ?"
    params.append(limit)
    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()  # type: ignore[type-error]


async def _like_search(
    conn: aiosqlite.Connection,
    query: str,
    tenant_id: str,
    project: str | None,
    fact_type: str | None,
    tags: list[str] | None,
    limit: int,
    as_of: str | None,
    confidence: str | None,
) -> list:
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.metadata,
               f.created_at, f.updated_at, f.tx_id, f.hash,
               f.consensus_score, f.confidence_rank
        FROM facts f
        WHERE f.tenant_id = ? AND f.content LIKE ?
    """
    params: list = [tenant_id, f"%{query}%"]
    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += " AND f.valid_until IS NULL"
    if project:
        sql += _PROJECT_FILTER
        params.append(project)
    if fact_type:
        sql += " AND f.fact_type = ?"
        params.append(fact_type)
    if tags:
        for tag in tags:
            sql += " AND json_extract(f.tags, '$') LIKE ?"
            params.append(f"%{tag}%")
    if confidence:
        sql += " AND f.confidence >= ?"
        params.append(confidence)
    sql += " ORDER BY f.updated_at DESC LIMIT ?"
    params.append(limit)
    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()  # type: ignore[type-error]


def text_search_sync(
    conn: sqlite3.Connection,
    query: str,
    tenant_id: str = "default",
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Full-text search (sync)."""
    use_fts = _has_fts5_sync(conn)
    try:
        if use_fts:
            fts_query = _sanitize_fts_query(query)
            sql = """
                SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
                       f.source, f.tags, bm25(facts_fts) AS rank
                FROM facts_fts fts JOIN facts f ON f.id = fts.rowid
                WHERE f.tenant_id = ? AND fts.content MATCH ? AND f.valid_until IS NULL
            """
            params: list = [tenant_id, fts_query]
            if project:
                sql += _PROJECT_FILTER
                params.append(project)
            sql += " ORDER BY rank ASC LIMIT ?"
            params.append(limit)
        else:
            sql = (
                "SELECT id, content, project, fact_type, confidence, source, tags "
                "FROM facts WHERE tenant_id = ? AND content LIKE ? AND valid_until IS NULL"
            )
            params = [tenant_id, f"%{query}%"]
            if project:
                sql += " AND project = ?"
                params.append(project)
            sql += " LIMIT ?"
            params.append(limit)

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error("Text search sync failed: %s", e)
        return []
    return [_parse_row_sync(row, use_fts) for row in rows]
