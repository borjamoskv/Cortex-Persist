"""
CORTEX v5.1 — Sovereign Connection Factory.

Single source of truth for ALL SQLite connections in the CORTEX ecosystem.
Every connection created through this module is guaranteed to have:
- WAL journal mode (concurrent reads during writes)
- busy_timeout of 5000ms (retry on lock instead of instant failure)
- NORMAL synchronous mode (performance without data loss)
- Foreign key enforcement

This module exists to make it ARCHITECTURALLY IMPOSSIBLE to create
an unprotected SQLite connection that could cause lock cascade hangs.

Usage (sync):
    from cortex.db import connect
    conn = connect("/path/to/db")

Usage (async):
    from cortex.db import connect_async, apply_pragmas_async
    conn = await connect_async("/path/to/db")
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Final

import aiosqlite

logger = logging.getLogger("cortex.db")

# ─── Configuration ────────────────────────────────────────────────────

# How long to wait (ms) for a locked database before raising OperationalError.
# 5 seconds is enough for most concurrent CLI + daemon scenarios.
BUSY_TIMEOUT_MS: Final[int] = 5000

# Python-level timeout (seconds) for the sqlite3.connect() call itself.
CONNECT_TIMEOUT_S: Final[int] = 10

# ─── Sync Factory ─────────────────────────────────────────────────────


def connect(
    db_path: str,
    *,
    check_same_thread: bool = False,
    row_factory: type | None = None,
    timeout: int = CONNECT_TIMEOUT_S,
) -> sqlite3.Connection:
    """Create a hardened sync SQLite connection.

    Every connection created through this factory is guaranteed to have
    WAL mode, busy_timeout, and foreign key enforcement enabled.

    Args:
        db_path: Path to the SQLite database file.
        check_same_thread: If False (default), allow cross-thread access.
        row_factory: Optional row factory (e.g., sqlite3.Row).
        timeout: Connection timeout in seconds.

    Returns:
        A fully-configured sqlite3.Connection.
    """
    conn = sqlite3.connect(
        db_path,
        timeout=timeout,
        check_same_thread=check_same_thread,
    )
    if row_factory is not None:
        conn.row_factory = row_factory
    _apply_pragmas_sync(conn)
    return conn


def _apply_pragmas_sync(conn: sqlite3.Connection) -> None:
    """Apply all mandatory pragmas to a sync connection."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")


# ─── Async Factory ────────────────────────────────────────────────────


async def connect_async(db_path: str) -> aiosqlite.Connection:
    """Create a hardened async SQLite connection.

    Equivalent to the sync factory but for aiosqlite.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A fully-configured aiosqlite.Connection.
    """
    conn = await aiosqlite.connect(db_path)
    await apply_pragmas_async(conn)
    return conn


async def apply_pragmas_async(conn: aiosqlite.Connection) -> None:
    """Apply all mandatory pragmas to an async connection.

    Use this when you can't use connect_async() directly
    (e.g., connection pool creates its own connections).
    """
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    await conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS};")
    await conn.commit()
