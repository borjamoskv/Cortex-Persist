# [C5-REAL] Exergy-Maximized
"""
Sovereign Connection Factory (KETER-∞ Metal-Level).

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

Usage (writer - disables auto WAL checkpoint):
    conn = connect_writer("/path/to/db")

Usage (async):
    from cortex.db import connect_async, apply_pragmas_async
    conn = await connect_async("/path/to/db")
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import os
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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

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

# -- Monkey-patch aiosqlite to propagate ContextVars to worker threads --
# This is mathematically required so that MTK capabilities (which use ContextVars)
# survive the hop from the main asyncio event loop thread to aiosqlite's background
# worker threads. Without this, the SQLite authorizer hook would always evaluate to None.
_original_aiosqlite_execute = aiosqlite.core.Connection._execute
_original_aiosqlite_cursor_execute = aiosqlite.core.Cursor._execute

def _patched_aiosqlite_execute(self, fn, *args, **kwargs):
    ctx = contextvars.copy_context()
    def wrapper():
        return ctx.run(fn, *args, **kwargs)
    return _original_aiosqlite_execute(self, wrapper)

def _patched_aiosqlite_cursor_execute(self, fn, *args, **kwargs):
    ctx = contextvars.copy_context()
    def wrapper():
        return ctx.run(fn, *args, **kwargs)
    return _original_aiosqlite_cursor_execute(self, wrapper)

aiosqlite.core.Connection._execute = _patched_aiosqlite_execute
aiosqlite.core.Cursor._execute = _patched_aiosqlite_cursor_execute
# ---------------------------------------------------------------------

try:
    import sqlite_vec
except ImportError:  # pragma: no cover - sqlite-vec is a base dependency in release builds
    sqlite_vec = None

# Python 3.12 deprecates the default datetime adapter. We register our own to prevent DeprecationWarning.
import datetime

from cortex.utils.errors import DBLockError

sqlite3.register_adapter(datetime.datetime, lambda val: val.isoformat())
sqlite3.register_adapter(datetime.date, lambda val: val.isoformat())

__all__ = [
    "apply_pragmas_async",
    "apply_pragmas_async_readonly",
    "connect",
    "connect_async",
    "connect_async_ctx",
    "connect_writer",
    "load_sqlite_vec_async",
]

logger = logging.getLogger("cortex.db")

# ─── Configuration ────────────────────────────────────────────────────

# How long to wait (ms) for a locked database before raising OperationalError.
# Rule R10 enforces 5000ms rigid boundary to prevent silent deadlocks.
BUSY_TIMEOUT_MS: Final[int] = 5000

# Python-level timeout (seconds) for the sqlite3.connect() call itself.
CONNECT_TIMEOUT_S: Final[int] = 5

# Memory-mapped I/O size (~20 GB). SQLite reads via kernel page cache
# instead of userspace read() syscalls. Zero-copy for hot paths.
MMAP_SIZE: Final[int] = 20_000_000_000

# Page size (bytes). 8KB aligns with SSD sector size and modern OS page
# caches. Only takes effect on new databases or after VACUUM; safe to set
# unconditionally (silent no-op on existing DBs).
PAGE_SIZE: Final[int] = 8192

# Negative value = KiB. Default 128MB. Configurable via CORTEX_SQLITE_CACHE_MB.
_CACHE_MB: Final[int] = int(os.environ.get("CORTEX_SQLITE_CACHE_MB", "128"))
CACHE_SIZE_KB: Final[int] = -(_CACHE_MB * 1024)

# WAL auto-checkpoint threshold (pages). At 8KB page_size, 1000 pages ≈ 8MB.
# Prevents unbounded WAL growth under sustained writes.
WAL_AUTOCHECKPOINT: Final[int] = 1000

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
    conn.execute(f"PRAGMA page_size={PAGE_SIZE}")
    conn.execute(f"PRAGMA cache_size={CACHE_SIZE_KB}")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA threads=4")  # Optimize sqlite-vec sorting/indexing

    if read_only:
        conn.execute("PRAGMA query_only=1")
    if writer_mode:
        # Disable automatic WAL checkpoints - writer controls flush timing
        conn.execute("PRAGMA wal_autocheckpoint=0")
    else:
        conn.execute(f"PRAGMA wal_autocheckpoint={WAL_AUTOCHECKPOINT}")

    # [MTK] C5-REAL Physical Boundary
    from cortex.engine.mtk_sqlite_authorizer import install_mtk_authorizer
    install_mtk_authorizer(conn)


# ─── Sync Factory ─────────────────────────────────────────────────────

class SovereignConnection(sqlite3.Connection):
    """Hardened connection class that prevents removing the MTK authorizer."""
    def set_authorizer(self, authorizer_callback: Any) -> None:
        from cortex.engine.mtk_sqlite_authorizer import mtk_authorizer_callback
        if authorizer_callback is not mtk_authorizer_callback:
            raise sqlite3.DatabaseError("MTK-LOCK: Cannot override sovereign authorizer callback.")
        super().set_authorizer(authorizer_callback)

def connect(
    db_path: str,
    *,
    uri: bool = False,
    check_same_thread: bool = False,
    row_factory: Any | None = None,
    timeout: int = CONNECT_TIMEOUT_S,
    read_only: bool = False,
    isolation_level: str | None = None,
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
        isolation_level: Optional isolation level for the connection.

    Returns:
        A fully-configured sqlite3.Connection.
    """
    try:
        conn = sqlite3.connect(
            db_path,
            timeout=timeout,
            check_same_thread=check_same_thread,
            uri=uri,
            factory=SovereignConnection,
            isolation_level=isolation_level,  # type: ignore[type-error]
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
    uri: bool = False,
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
            factory=SovereignConnection,
            uri=uri,
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
    uri: bool = False,
) -> aiosqlite.Connection:
    """Create a hardened async SQLite connection.

    Equivalent to the sync factory but for aiosqlite.

    Args:
        db_path: Path to the SQLite database file.
        read_only: If True, enforce query_only=1.
        uri: If True, allow URI filename parsing.
    """
    is_uri = uri or db_path.startswith("file:")
    try:
        conn = await aiosqlite.connect(db_path, timeout=5.0, uri=is_uri, factory=SovereignConnection)
    except sqlite3.OperationalError as e:
        if any(m in str(e).lower() for m in _LOCK_MARKERS):
            raise DBLockError(f"Async database lock timeout: {e}") from e
        raise

    if read_only:
        await apply_pragmas_async_readonly(conn)
    else:
        await apply_pragmas_async(conn)

    conn._cortex_db_path = str(db_path)
    try:
        conn._cortex_loop = asyncio.get_running_loop()
    except RuntimeError:
        conn._cortex_loop = None

    return conn


@asynccontextmanager
async def connect_async_ctx(
    db_path: str,
    *,
    read_only: bool = False,
    uri: bool = False,
) -> AsyncIterator[aiosqlite.Connection]:
    """Context manager wrapping connect_async().

    Drop-in replacement for ``async with aiosqlite.connect(path)``
    that guarantees WAL, busy_timeout, and all sovereign pragmas.

    Usage::

        async with connect_async_ctx("/path/to/db") as conn:
            await conn.execute("SELECT 1")
    """
    conn = await connect_async(db_path, read_only=read_only, uri=uri)
    try:
        yield conn
    finally:
        await conn.close()


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
    await conn.execute(f"PRAGMA page_size={PAGE_SIZE};")
    await conn.execute(f"PRAGMA cache_size={CACHE_SIZE_KB};")
    await conn.execute("PRAGMA temp_store=MEMORY;")
    await conn.execute("PRAGMA threads=4;")  # Optimize sqlite-vec sorting/indexing
    await conn.execute(f"PRAGMA wal_autocheckpoint={WAL_AUTOCHECKPOINT};")
    
    # [MTK] C5-REAL Physical Boundary
    def _install_authorizer_sync(raw_conn: sqlite3.Connection):
        from cortex.engine.mtk_sqlite_authorizer import install_mtk_authorizer
        install_mtk_authorizer(raw_conn)
        
    await conn._execute(_install_authorizer_sync, conn._conn)
    await conn.commit()


async def apply_pragmas_async_readonly(conn: aiosqlite.Connection) -> None:
    """Apply read-only pragmas to an async connection.

    Sets query_only=1 so any INSERT/UPDATE/DELETE raises OperationalError
    at the SQLite level - defense in depth for read pools.
    """
    await apply_pragmas_async(conn)
    await conn.execute("PRAGMA query_only=1;")
    await conn.commit()


async def load_sqlite_vec_async(conn: aiosqlite.Connection) -> bool:
    """Load sqlite-vec into an async connection when the runtime supports it."""
    if sqlite_vec is None:
        return False

    extension_toggle_enabled = False
    try:
        await conn.enable_load_extension(True)
        extension_toggle_enabled = True
        await conn._execute(sqlite_vec.load, conn._conn)
    except (AttributeError, OSError, sqlite3.Error) as exc:
        logger.debug("sqlite-vec not available for async connection: %s", exc)
        return False
    finally:
        if extension_toggle_enabled:
            try:
                await conn.enable_load_extension(False)
            except (AttributeError, OSError, sqlite3.Error):
                logger.debug("sqlite-vec cleanup skipped for async connection")

    return True
