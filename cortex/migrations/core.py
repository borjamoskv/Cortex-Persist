"""
CORTEX v5.0 — Schema Migrations Core.
"""

from __future__ import annotations

import logging
import sqlite3

import aiosqlite

from cortex.database.schema import get_all_schema
from cortex.migrations.registry import MIGRATIONS

__all__ = [
    "ensure_migration_table",
    "get_current_version",
    "run_migrations",
    "run_migrations_async",
]

logger = logging.getLogger("cortex")


def ensure_migration_table(conn: sqlite3.Connection):
    """Create the schema_version table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    conn.commit()


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version (0 means fresh DB)."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row[0] is not None else 0
    except (sqlite3.Error, OSError):
        return 0


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run all pending migrations."""
    ensure_migration_table(conn)
    current = get_current_version(conn)

    if current == 0:
        _apply_base_schema(conn)

    applied = 0
    for version, description, func in MIGRATIONS:
        if version > current:
            if _apply_migration_sync(conn, version, description, func):
                applied += 1

    if applied:
        logger.info(
            "Applied %d migration(s). Schema now at version %d", applied, get_current_version(conn)
        )
    return applied


def _apply_base_schema(conn: sqlite3.Connection) -> None:
    """Apply base schema if database is fresh."""
    logger.info("Fresh database detected. Applying base schema...")
    for stmt in get_all_schema():
        try:
            conn.executescript(stmt)
        except (sqlite3.Error, OSError) as e:
            msg = str(e).lower()
            if "vec0" in str(stmt) or "no such module" in msg or "duplicate column" in msg:
                logger.warning("Skipping schema statement: %s", e)
            else:
                raise
    conn.commit()
    logger.info("Base schema applied.")


def _apply_migration_sync(conn: sqlite3.Connection, version: int, description: str, func) -> bool:
    """Apply a single migration synchronously."""
    logger.info("Applying migration %d: %s", version, description)
    try:
        func(conn)
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (version, description),
        )
        conn.commit()
        return True
    except (sqlite3.Error, OSError) as e:
        logger.error("Migration %d failed: %s. Skipping.", version, e)
        conn.rollback()
        return False


async def run_migrations_async(conn: aiosqlite.Connection) -> int:
    """Async version of run_migrations."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    await conn.commit()

    cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    current = row[0] if row and row[0] is not None else 0

    if current == 0:
        await _apply_base_schema_async(conn)

    applied = 0
    for version, description, func in MIGRATIONS:
        if version > current:
            if await _apply_migration_async(conn, version, description, func):
                applied += 1
    return applied


async def _apply_base_schema_async(conn: aiosqlite.Connection) -> None:
    """Apply base schema asynchronously."""
    logger.info("Fresh database detected. Applying base schema (async)...")
    for stmt in get_all_schema():
        try:
            await conn.executescript(stmt)
        except (sqlite3.Error, OSError) as e:
            msg = str(e).lower()
            if "vec0" in str(stmt) or "no such module" in msg or "duplicate column" in msg:
                logger.warning("Skipping schema statement: %s", e)
            else:
                raise
    await conn.commit()


async def _apply_migration_async(
    conn: aiosqlite.Connection, version: int, description: str, func
) -> bool:
    """Apply a single migration asynchronously."""
    logger.info("Applying async migration %d: %s", version, description)
    try:
        # Run sync migration func on aiosqlite internal worker thread
        await conn._execute(func, conn._conn)
        await conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (version, description),
        )
        await conn.commit()
        return True
    except (sqlite3.Error, OSError) as e:
        logger.error("Migration %d failed: %s", version, e)
        await conn.rollback()
        return False
