"""
CORTEX v5.2 — Sovereign Connection Factory (KETER-∞ Metal-Level).

Single source of truth for ALL SQLite connections in the CORTEX ecosystem.
Every connection created through this module is guaranteed to have:
- WAL journal mode (concurrent reads during writes)
- busy_timeout of 5000ms (retry on lock instead of instant failure)
- NORMAL synchronous mode (performance without data loss)
- Foreign key enforcement
- mmap I/O (bypasses read() syscalls via kernel page cache)

This module exists to make it ARCHITECTURALLY IMPOSSIBLE to create
an unprotected SQLite connection that could cause lock cascade hangs.

Usage (sync):
    from cortex.db import connect
    conn = connect("/path/to/db")

Usage (read-only pool):
    conn = connect("/path/to/db", read_only=True)

Usage (writer — disables auto WAL checkpoint):
    conn = connect_writer("/path/to/db")

Usage (async):
    from cortex.db import connect_async, apply_pragmas_async
    conn = await connect_async("/path/to/db")
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Final

import aiosqlite

from cortex.errors import DBLockError

__all__ = [
    "connect",
    "connect_writer",
    "connect_async",
    "apply_pragmas_async",
    "apply_pragmas_async_readonly",
]

logger = logging.getLogger("cortex.db")

# ─── Configuration ────────────────────────────────────────────────────

# How long to wait (ms) for a locked database before raising OperationalError.
BUSY_TIMEOUT_MS: Final[int] = 5000

# Python-level timeout (seconds) for the sqlite3.connect() call itself.
CONNECT_TIMEOUT_S: Final[int] = 10

# Memory-mapped I/O size (~20 GB). SQLite reads via kernel page cache
# instead of userspace read() syscalls. Zero-copy for hot paths.
MMAP_SIZE: Final[int] = 20_000_000_000

# Strings used to detect lock errors in OperationalError messages.
_LOCK_MARKERS: Final[tuple[str, ...]] = ("database is locked", "busy")


# ─── Core Pragmas ─────────────────────────────────────────────────────


def _apply_pragmas_sync(
    conn: sqlite3.Connection,
    *,
    read_only: bool = False,
    writer_mode: bool = False,
) -> None:
    """Apply all mandatory pragmas to a sync connection.

    Args:
        read_only: If True, set query_only=1 (rejects all writes at SQLite level).
        writer_mode: If True, disable wal_autocheckpoint (manual control).
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute(f"PRAGMA mmap_size={MMAP_SIZE}")

    if read_only:
        conn.execute("PRAGMA query_only=1")
    if writer_mode:
        # Disable automatic WAL checkpoints — writer controls flush timing
        conn.execute("PRAGMA wal_autocheckpoint=0")


# ─── Sync Factory ─────────────────────────────────────────────────────


def connect(
    db_path: str,
    *,
    check_same_thread: bool = False,
    row_factory: type | None = None,
    timeout: int = CONNECT_TIMEOUT_S,
    read_only: bool = False,
) -> sqlite3.Connection:
    """Create a hardened sync SQLite connection.

    Every connection created through this factory is guaranteed to have
    WAL mode, busy_timeout, mmap I/O, and foreign key enforcement enabled.

    Args:
        db_path: Path to the SQLite database file.
        check_same_thread: If False (default), allow cross-thread access.
        row_factory: Optional row factory (e.g., sqlite3.Row).
        timeout: Connection timeout in seconds.
        read_only: If True, enforce query_only=1 (no writes allowed).

    Returns:
        A fully-configured sqlite3.Connection.
    """
    try:
        conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            check_same_thread=check_same_thread,
        )
    except sqlite3.OperationalError as e:
        if any(m in str(e).lower() for m in _LOCK_MARKERS):
            raise DBLockError(f"Database lock timeout after {timeout}s: {e}") from e
        raise

    if row_factory is not None:
        conn.row_factory = row_factory
    _apply_pragmas_sync(conn, read_only=read_only)
    return conn


def connect_writer(
    db_path: str,
    *,
    check_same_thread: bool = False,
    timeout: int = CONNECT_TIMEOUT_S,
) -> sqlite3.Connection:
    """Create a hardened sync connection for the single-writer thread.

    Disables wal_autocheckpoint so the writer controls WAL flush timing.
    This prevents surprise latency spikes during inference bursts.

    Args:
        db_path: Path to the SQLite database file.
        check_same_thread: If False (default), allow cross-thread access.
        timeout: Connection timeout in seconds.

    Returns:
        A writer-optimized sqlite3.Connection.
    """
    try:
        conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            check_same_thread=check_same_thread,
        )
    except sqlite3.OperationalError as e:
        if any(m in str(e).lower() for m in _LOCK_MARKERS):
            raise DBLockError(f"Writer lock timeout after {timeout}s: {e}") from e
        raise

    _apply_pragmas_sync(conn, writer_mode=True)
    return conn


# ─── Async Factory ────────────────────────────────────────────────────


async def connect_async(
    db_path: str,
    *,
    read_only: bool = False,
) -> aiosqlite.Connection:
    """Create a hardened async SQLite connection.

    Equivalent to the sync factory but for aiosqlite.

    Args:
        db_path: Path to the SQLite database file.
        read_only: If True, enforce query_only=1.

    Returns:
        A fully-configured aiosqlite.Connection.
    """
    try:
        conn = await aiosqlite.connect(db_path)
    except sqlite3.OperationalError as e:
        if any(m in str(e).lower() for m in _LOCK_MARKERS):
            raise DBLockError(f"Async database lock timeout: {e}") from e
        raise

    if read_only:
        await apply_pragmas_async_readonly(conn)
    else:
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
    await conn.execute(f"PRAGMA mmap_size={MMAP_SIZE};")
    await conn.commit()


async def apply_pragmas_async_readonly(conn: aiosqlite.Connection) -> None:
    """Apply read-only pragmas to an async connection.

    Sets query_only=1 so any INSERT/UPDATE/DELETE raises OperationalError
    at the SQLite level — defense in depth for read pools.
    """
    await apply_pragmas_async(conn)
    await conn.execute("PRAGMA query_only=1;")
    await conn.commit()
