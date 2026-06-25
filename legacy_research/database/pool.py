# [C5-REAL] Exergy-Maximized
"""
Async Connection Pool.

Production-grade asyncio connection pool for SQLite databases.
Handles connection lifecycle, health checks, and WAL mode optimization.
"""

from __future__ import annotations

import asyncio
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
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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

from legacy_research.extensions.immune.chaos import ChaosGate, async_interceptor

__all__ = ["CortexConnectionPool"]

logger = logging.getLogger("cortex.pool")


class CortexConnectionPool:
    """
    Production-grade connection pool for CORTEX.

    Features:
    - Min/max connection bounds
    - Connection health checks
    - Automatic reconnection
    - WAL mode optimization
    - Thread-safe asyncio primitives
    """

    def __init__(
        self,
        db_path: str,
        min_connections: int | None = None,
        max_connections: int | None = None,
        max_idle_time: float = 300.0,
        read_only: bool = True,
    ):
        _env_min = int(os.environ.get("CORTEX_POOL_MIN", "4"))
        _env_max = int(os.environ.get("CORTEX_POOL_MAX", "32"))
        self.db_path = db_path
        self.min_connections = min_connections or _env_min
        self.max_connections = max_connections or _env_max
        self.max_idle_time = max_idle_time
        self.read_only = read_only

        self.chaos_gate = ChaosGate(name=f"sqlite_pool:{self.db_path}")
        self._local = threading.local()

    def _get_local_state(self):
        """Get or initialize thread-local pool state."""
        if not hasattr(self._local, "pool"):
            self._local.pool = asyncio.Queue()
            self._local.active_count = 0
            self._local.lock = asyncio.Lock()
            self._local.semaphore = asyncio.Semaphore(self.max_connections)
            self._local.initialized = False
        return self._local

    @property
    def _initialized(self) -> bool:
        return self._get_local_state().initialized

    @property
    def _active_count(self) -> int:
        return self._get_local_state().active_count

    @property
    def _pool(self) -> asyncio.Queue:
        return self._get_local_state().pool

    async def initialize(self) -> None:
        """Pre-warm pool with min_connections."""
        state = self._get_local_state()
        if state.initialized:
            return

        logger.info(
            "Initializing connection pool (min=%d, max=%d) at %s",
            self.min_connections,
            self.max_connections,
            self.db_path,
        )

        async with state.lock:
            # Check again under lock
            if state.initialized:
                return

            for _ in range(self.min_connections):
                conn = await self._create_connection()
                await state.pool.put(conn)
                state.active_count += 1
            state.initialized = True

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a highly-optimized, WAL-enabled async connection."""
        from cortex.database.core import connect_async, load_sqlite_vec_async

        try:
            conn = await connect_async(self.db_path, read_only=self.read_only)
        except (sqlite3.Error, OSError) as e:
            logger.critical("Failed to create DB connection: %s", e)
            raise

        await load_sqlite_vec_async(conn)

        return conn

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Acquire a connection from the pool."""
        state = self._get_local_state()
        if not state.initialized:
            await self.initialize()

        # Enforce max concurrency
        await state.semaphore.acquire()
        conn: aiosqlite.Connection | None = None

        try:
            # 1. Get or create connection
            conn = await self._get_or_create_conn()

            # 2. Health check and potential replacement
            conn = await self._ensure_healthy_conn(conn)

            yield conn

        except (sqlite3.Error, OSError):
            if conn:
                await self._close_conn(conn)
                conn = None
            raise

        finally:
            state.semaphore.release()
            if conn:
                await state.pool.put(conn)

    async def _get_or_create_conn(self) -> aiosqlite.Connection:
        """Get a connection from the pool or create a new one."""
        state = self._get_local_state()
        try:
            return state.pool.get_nowait()
        except asyncio.QueueEmpty:
            conn = await self._create_connection()
            async with state.lock:
                state.active_count += 1
            return conn

    async def _ensure_healthy_conn(self, conn: aiosqlite.Connection) -> aiosqlite.Connection:
        """Ensure the connection is healthy, replacing it if necessary."""
        if await self._is_healthy(conn):
            return conn

        logger.warning("Connection unhealthy, replacing.")
        await self._close_conn(conn)
        new_conn = await self._create_connection()
        state = self._get_local_state()
        async with state.lock:
            state.active_count += 1
        return new_conn

    async def _is_healthy(self, conn: aiosqlite.Connection) -> bool:
        """Check if connection is alive. Logic-bombed by chaos_gate."""

        async def _check():
            async with conn.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            return True

        try:
            return await async_interceptor(self.chaos_gate, _check)
        except (sqlite3.Error, OSError, ConnectionError, TimeoutError):
            return False

    async def _close_conn(self, conn: aiosqlite.Connection) -> None:
        """Safely close a connection."""
        try:
            await conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.warning("Error closing connection: %s", e)
        state = self._get_local_state()
        async with state.lock:
            state.active_count = max(0, state.active_count - 1)

    async def close(self) -> None:
        """Close all connections in the pool."""
        logger.info("Closing connection pool...")
        state = self._get_local_state()
        while not state.pool.empty():
            try:
                conn = state.pool.get_nowait()
                await self._close_conn(conn)
            except asyncio.QueueEmpty:
                break
        state.initialized = False
