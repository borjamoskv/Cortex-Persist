"""CORTEX v8 — Federated Search Engine.

Enables transparent search across partitioned memory databases:
  - core     → ~/.cortex/cortex.db (CORTEX infra, IA, tooling)
  - personal → ~/.cortex/personal_memories.db (side projects)
  - cold     → ~/.cortex/cold_storage.db (tests, archived junk)
  - all      → union of all three

Architecture: ATTACH DATABASE (SQLite native) for zero-copy
cross-database queries. Each result carries `db_origin` provenance.

Usage:
    from cortex.search.federation import federated_search_sync
    results = federated_search_sync(conn, "NAROA routing", scope="all")
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from cortex.core.paths import COLD_STORAGE_DB, PERSONAL_DB
from cortex.search.models import SearchResult, SearchScope
from cortex.search.text import text_search_sync

__all__ = ["federated_search_sync", "attach_federated_dbs"]

logger = logging.getLogger("cortex.search.federation")

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
            logger.debug("Skipping %s — %s not found", alias, db_path)
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


def detach_federated_dbs(
    conn: sqlite3.Connection,
    aliases: list[str],
) -> None:
    """DETACH previously attached databases."""
    for alias in aliases:
        try:
            conn.execute(f"DETACH DATABASE {alias}")
        except sqlite3.OperationalError:
            pass


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
    from cortex.crypto import get_default_encrypter
    from cortex.crypto.aes import CortexEncrypter

    enc = get_default_encrypter()
    v6_prefix = CortexEncrypter.PREFIX

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
        content_raw = row[1] or ""
        if str(content_raw).startswith(v6_prefix):
            try:
                content = enc.decrypt_str(content_raw, tenant_id="default")
            except Exception:
                continue
        else:
            content = str(content_raw)

        if query_lower not in content.lower():
            continue

        try:
            tags = __import__("json").loads(row[6]) if row[6] else []
        except (ValueError, TypeError):
            tags = []

        results.append(SearchResult(
            fact_id=row[0],
            content=content,
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
        ))

        if len(results) >= limit:
            break

    return results


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
            conn, query, project=project, limit=limit,
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
                    conn, alias, query,
                    project=project, limit=limit,
                )
                all_results.extend(fed_results)
        finally:
            detach_federated_dbs(conn, attached)

    # Sort merged results by score descending
    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results[:limit]
