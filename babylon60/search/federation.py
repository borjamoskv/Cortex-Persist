# [C5-REAL] Exergy-Maximized
"""Federated Search Engine.

Enables transparent search across partitioned memory databases:
  - core     → ~/.cortex/cortex.db (CORTEX infra, IA, tooling)
  - personal → ~/.cortex/personal_memories.db (side projects)
  - cold     → ~/.cortex/cold_storage.db (tests, archived junk)
  - all      → union of all three

Architecture: ATTACH DATABASE (SQLite native) for zero-copy
cross-database queries. Each result carries `db_origin` provenance.

Usage:
    from babylon60.search.federation import federated_search_sync
    results = federated_search_sync(conn, "NAROA routing", scope="all")
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import aiosqlite

from babylon60.core.paths import COLD_STORAGE_DB, PERSONAL_DB
from babylon60.search.models import SearchResult, SearchScope
from babylon60.search.text import text_search, text_search_sync

__all__ = [
    "attach_federated_dbs",
    "attach_federated_dbs_async",
    "federated_search",
    "federated_search_sync",
]

logger = logging.getLogger("babylon60.search.federation")

# Alias map: scope name → (db_path, attach_alias)
_FEDERATION_MAP: dict[str, tuple[Path, str]] = {
    "personal": (PERSONAL_DB, "personal"),
    "cold": (COLD_STORAGE_DB, "cold"),
}


def attach_federated_dbs(
    conn: sqlite3.Connection,
    scopes: list[str] | None = None,
) -> list[str]:
    """ATTACH secondary databases to an existing connection.

    Returns list of successfully attached aliases.
    Only attaches databases that exist on disk.
    """
    targets = scopes or list(_FEDERATION_MAP.keys())
    attached: list[str] = []

    for scope_name in targets:
        if scope_name not in _FEDERATION_MAP:
            continue
        db_path, alias = _FEDERATION_MAP[scope_name]
        if not db_path.exists():
            logger.debug("Skipping %s - %s not found", alias, db_path)
            continue
        valid_aliases = [v[1] for v in _FEDERATION_MAP.values()]
        if alias not in valid_aliases:
            continue

        try:
            conn.execute(
                f"ATTACH DATABASE ? AS {alias}",
                (str(db_path),),
            )
            attached.append(alias)
            logger.debug("Attached %s → %s", alias, db_path)
        except sqlite3.OperationalError as e:
            if "already" in str(e).lower():
                attached.append(alias)
            else:
                logger.warning("Failed to attach %s: %s", alias, e)

    return attached


async def attach_federated_dbs_async(
    conn: aiosqlite.Connection,
    scopes: list[str] | None = None,
) -> list[str]:
    """ATTACH secondary databases to an existing async connection."""
    targets = scopes or list(_FEDERATION_MAP.keys())
    attached: list[str] = []

    for scope_name in targets:
        if scope_name not in _FEDERATION_MAP:
            continue
        db_path, alias = _FEDERATION_MAP[scope_name]
        if not db_path.exists():
            continue

        try:
            await conn.execute(f"ATTACH DATABASE ? AS {alias}", (str(db_path),))
            attached.append(alias)
        except (aiosqlite.Error, sqlite3.Error) as e:
            if "already" in str(e).lower():
                attached.append(alias)
            else:
                logger.warning("Failed to attach %s: %s", alias, e)

    return attached


def detach_federated_dbs(
    conn: sqlite3.Connection,
    aliases: list[str],
) -> None:
    """DETACH previously attached databases."""
    valid_aliases = [v[1] for v in _FEDERATION_MAP.values()]
    for alias in aliases:
        if alias not in valid_aliases:
            continue
        try:
            conn.execute(f"DETACH DATABASE {alias}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Suppressed exception: %s", exc)


async def detach_federated_dbs_async(
    conn: aiosqlite.Connection,
    aliases: list[str],
) -> None:
    """DETACH previously attached databases (async)."""
    valid_aliases = [v[1] for v in _FEDERATION_MAP.values()]
    for alias in aliases:
        if alias not in valid_aliases:
            continue
        try:
            await conn.execute(f"DETACH DATABASE {alias}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Suppressed exception: %s", exc)


def _search_attached_db(
    conn: sqlite3.Connection,
    alias: str,
    query: str,
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Search an attached database's facts table.

    Handles AES-GCM encrypted content by decrypting client-side.
    Falls back to LIKE for unencrypted DBs.
    """
    from babylon60.crypto import get_default_encrypter
    from babylon60.crypto.aes import CortexEncrypter

    enc = get_default_encrypter()
    v6_prefix = CortexEncrypter.PREFIX

    valid_aliases = [v[1] for v in _FEDERATION_MAP.values()]
    if alias not in valid_aliases:
        return []

    # Fetch active facts (capped at 500 to limit memory)
    sql = (
        f"SELECT f.id, f.content, f.project, f.fact_type, "
        f"f.confidence, f.source, f.tags "
        f"FROM {alias}.facts f "
        f"WHERE f.valid_until IS NULL"
    )
    params: list = []
    if project:
        sql += " AND f.project = ?"
        params.append(project)
    sql += " LIMIT 500"

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.warning("Search on %s failed: %s", alias, e)
        return []

    # Decrypt and filter client-side
    query_lower = query.lower()
    results: list[SearchResult] = []

    for row in rows:
        if str(row[1]).startswith(v6_prefix):
            try:
                content = enc.decrypt_str(row[1], tenant_id="default")
            except (ValueError, TypeError, OSError):
                continue
        else:
            content = str(row[1])

        if content is None:
            continue

        content = content or ""
        if query_lower not in content.lower():
            continue

        try:
            tags = __import__("json").loads(row[6]) if row[6] else []
        except (ValueError, TypeError):
            tags = []

        results.append(
            SearchResult(
                fact_id=row[0],
                content=content,  # type: ignore[type-error]
                project=row[2] or "",
                fact_type=row[3] or "knowledge",
                confidence=row[4] or "stated",
                source=row[5],
                tags=tags,
                score=0.5,
                valid_from="unknown",
                valid_until=None,
                created_at="unknown",
                updated_at="unknown",
                db_origin=alias,
            )
        )

        if len(results) >= limit:
            break

    return results


async def _search_attached_db_async(
    conn: aiosqlite.Connection,
    alias: str,
    query: str,
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Search an attached database's facts table (async)."""
    from babylon60.crypto import get_default_encrypter
    from babylon60.crypto.aes import CortexEncrypter

    enc = get_default_encrypter()
    v6_prefix = CortexEncrypter.PREFIX

    valid_aliases = [v[1] for v in _FEDERATION_MAP.values()]
    if alias not in valid_aliases:
        return []

    sql = (
        f"SELECT f.id, f.content, f.project, f.fact_type, "
        f"f.confidence, f.source, f.tags "
        f"FROM {alias}.facts f "
        f"WHERE f.valid_until IS NULL"
    )
    params: list = []
    if project:
        sql += " AND f.project = ?"
        params.append(project)
    sql += " LIMIT 500"

    try:
        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
    except (aiosqlite.Error, sqlite3.Error) as e:
        logger.warning("Search on %s failed: %s", alias, e)
        return []

    query_lower = query.lower()
    results: list[SearchResult] = []

    for row in rows:
        content_val = row[1]
        if str(content_val).startswith(v6_prefix):
            try:
                content = enc.decrypt_str(content_val, tenant_id="default")
            except (ValueError, TypeError, OSError):
                continue
        else:
            content = str(content_val)

        if content is None or query_lower not in content.lower():
            continue

        try:
            tags = __import__("json").loads(row[6]) if row[6] else []
        except (ValueError, TypeError):
            tags = []

        results.append(
            SearchResult(
                fact_id=row[0],
                content=content,  # type: ignore[type-error]
                project=row[2] or "",
                fact_type=row[3] or "knowledge",
                confidence=row[4] or "stated",
                source=row[5],
                tags=tags,
                score=0.5,
                valid_from="unknown",
                valid_until=None,
                created_at="unknown",
                updated_at="unknown",
                db_origin=alias,
            )
        )

        if len(results) >= limit:
            break

    return results


async def federated_search(
    conn: aiosqlite.Connection,
    query: str,
    scope: str = "core",
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Federated text search across (async)."""
    try:
        search_scope = SearchScope(scope)
    except ValueError:
        search_scope = SearchScope.CORE

    all_results: list[SearchResult] = []

    if search_scope in (SearchScope.CORE, SearchScope.ALL):
        core_results = await text_search(
            conn,
            query,
            project=project,
            limit=limit,
        )
        for r in core_results:
            r.db_origin = "core"
        all_results.extend(core_results)

    if search_scope in (SearchScope.PERSONAL, SearchScope.ALL):
        targets = ["personal"]
    elif search_scope == SearchScope.COLD:
        targets = ["cold"]
    elif search_scope == SearchScope.ALL:
        targets = ["personal", "cold"]
    else:
        targets = []

    if targets:
        attached = await attach_federated_dbs_async(conn, targets)
        try:
            for alias in attached:
                fed_results = await _search_attached_db_async(
                    conn,
                    alias,
                    query,
                    project=project,
                    limit=limit,
                )
                all_results.extend(fed_results)
        finally:
            await detach_federated_dbs_async(conn, attached)

    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results[:limit]


def federated_search_sync(
    conn: sqlite3.Connection,
    query: str,
    scope: str = "core",
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Federated text search across partitioned databases.

    Args:
        conn: Connection to the main (core) database.
        query: Search query string.
        scope: One of 'core', 'personal', 'cold', 'all'.
        project: Optional project filter.
        limit: Max results per database.

    Returns:
        Merged list of SearchResult, each tagged with db_origin.
    """
    try:
        search_scope = SearchScope(scope)
    except ValueError:
        logger.warning("Invalid scope '%s', falling back to core", scope)
        search_scope = SearchScope.CORE

    all_results: list[SearchResult] = []

    # Core search (always uses the main connection)
    if search_scope in (SearchScope.CORE, SearchScope.ALL):
        core_results = text_search_sync(
            conn,
            query,
            project=project,
            limit=limit,
        )
        for r in core_results:
            r.db_origin = "core"
        all_results.extend(core_results)

    # Federated databases
    if search_scope in (SearchScope.PERSONAL, SearchScope.ALL):
        targets = ["personal"]
    elif search_scope == SearchScope.COLD:
        targets = ["cold"]
    elif search_scope == SearchScope.ALL:
        targets = ["personal", "cold"]
    else:
        targets = []

    if targets:
        attached = attach_federated_dbs(conn, targets)
        try:
            for alias in attached:
                fed_results = _search_attached_db(
                    conn,
                    alias,
                    query,
                    project=project,
                    limit=limit,
                )
                all_results.extend(fed_results)
        finally:
            detach_federated_dbs(conn, attached)

    # Sort merged results by score descending
    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results[:limit]
