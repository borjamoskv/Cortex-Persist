"""
CORTEX v5.0 — Async Connection Pool.

Production-grade asyncio connection pool for SQLite databases.
Handles connection lifecycle, health checks, and WAL mode optimization.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

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
        min_connections: int = 2,
        max_connections: int = 10,
        max_idle_time: float = 300.0,
        read_only: bool = True,
    ):
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.read_only = read_only

        self._pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue()
        self._active_count = 0
        self._lock = asyncio.Lock()
        # Semaphore limits concurrent acquisitions
        self._semaphore = asyncio.Semaphore(max_connections)
        self._initialized = False

    async def initialize(self) -> None:
        """Pre-warm pool with min_connections."""
        if self._initialized:
            return

        logger.info(
            "Initializing connection pool (min=%d, max=%d) at %s",
            self.min_connections,
            self.max_connections,
            self.db_path,
        )

        async with self._lock:
            # Check again under lock
            if self._initialized:
                return

            for _ in range(self.min_connections):
                conn = await self._create_connection()
                await self._pool.put(conn)
                self._active_count += 1
            self._initialized = True

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a highly-optimized, WAL-enabled async connection."""
        from cortex.database.core import connect_async

        try:
            conn = await connect_async(self.db_path, read_only=self.read_only)
        except (sqlite3.Error, OSError) as e:
            logger.critical("Failed to create DB connection: %s", e)
            raise

        # Wave 5: Load Vector Extension
        try:
            import sqlite_vec

            await conn.enable_load_extension(True)
            await conn.load_extension(sqlite_vec.loadable_path())
            await conn.enable_load_extension(False)
        except (ImportError, OSError, AttributeError) as e:
            logger.debug(f"sqlite-vec not available for connection: {e}")

        return conn

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Acquire a connection from the pool."""
        if not self._initialized:
            await self.initialize()

        # Enforce max concurrency
        await self._semaphore.acquire()
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
            self._semaphore.release()
            if conn:
                await self._pool.put(conn)

    async def _get_or_create_conn(self) -> aiosqlite.Connection:
        """Get a connection from the pool or create a new one."""
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            conn = await self._create_connection()
            async with self._lock:
                self._active_count += 1
            return conn

    async def _ensure_healthy_conn(self, conn: aiosqlite.Connection) -> aiosqlite.Connection:
        """Ensure the connection is healthy, replacing it if necessary."""
        if await self._is_healthy(conn):
            return conn

        logger.warning("Connection unhealthy, replacing.")
        await self._close_conn(conn)
        new_conn = await self._create_connection()
        async with self._lock:
            self._active_count += 1
        return new_conn


    async def _is_healthy(self, conn: aiosqlite.Connection) -> bool:
        """Check if connection is alive."""
        try:
            async with conn.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            return True
        except (sqlite3.Error, OSError):
            return False

    async def _close_conn(self, conn: aiosqlite.Connection) -> None:
        """Safely close a connection."""
        try:
            await conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.warning("Error closing connection: %s", e)
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)

    async def close(self) -> None:
        """Close all connections in the pool."""
        logger.info("Closing connection pool...")
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await self._close_conn(conn)
            except asyncio.QueueEmpty:
                break
        self._initialized = False
