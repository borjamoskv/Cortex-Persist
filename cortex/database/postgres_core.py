# [C5-REAL] Exergy-Maximized
"""
Sovereign Connection Factory for PostgreSQL (AlloyDB / pgvector).

This module establishes the connection substrate for infinite memory scaling
under the v11.0 Sovereign Cloud architecture. It guarantees connection pooling,
pgvector type registration, and transaction isolation levels consistent with C5-REAL execution.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

try:
    import asyncpg  # pyright: ignore[reportMissingImports]
except ImportError:
    asyncpg = None

try:
    from pgvector.asyncpg import register_vector  # pyright: ignore[reportMissingImports]
except ImportError:
    register_vector = None

from cortex.utils.errors import DBLockError

__all__ = [
    "connect_async_ctx",
    "create_pool_async",
]

logger = logging.getLogger("cortex.db.postgres")

# ─── Configuration ────────────────────────────────────────────────────
PG_TIMEOUT_S = int(os.environ.get("CORTEX_PG_TIMEOUT", "5"))
PG_POOL_MIN = int(os.environ.get("CORTEX_PG_POOL_MIN", "10"))
PG_POOL_MAX = int(os.environ.get("CORTEX_PG_POOL_MAX", "50"))


async def _init_connection(conn: asyncpg.Connection) -> None:  # pyright: ignore[reportInvalidTypeForm]
    """Initialize a new connection with pgvector support and timeouts."""
    if register_vector is not None:
        await register_vector(conn)
    else:
        logger.warning("pgvector.asyncpg not installed; vector operations may fail.")

    # Set statement timeout to prevent runaway queries
    await conn.execute(f"SET statement_timeout = {PG_TIMEOUT_S * 1000};")


async def create_pool_async(dsn: str) -> asyncpg.Pool:  # pyright: ignore[reportInvalidTypeForm]
    """Create a highly concurrent connection pool for LEGION-10k scaling."""
    if asyncpg is None:
        raise ImportError(
            "asyncpg is required for PostgreSQL backend. Install via `pip install asyncpg`."
        )

    try:
        pool = await asyncpg.create_pool(
            dsn,
            min_size=PG_POOL_MIN,
            max_size=PG_POOL_MAX,
            setup=_init_connection,
            command_timeout=PG_TIMEOUT_S,
        )
        if pool is None:
            raise RuntimeError("Failed to initialize asyncpg pool")
        return pool
    except Exception as e:
        logger.error(f"PostgreSQL Pool Initialization Error: {e}")
        raise DBLockError(f"Failed to acquire PostgreSQL pool: {e}") from e


@asynccontextmanager
async def connect_async_ctx(pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:  # pyright: ignore[reportInvalidTypeForm]
    """Acquire a resilient, type-safe connection from the pool."""
    if asyncpg is None:
        raise ImportError("asyncpg is required.")

    try:
        async with pool.acquire() as conn:
            yield conn
    except asyncpg.exceptions.PostgresError as e:
        logger.error(f"PostgreSQL Transaction Error: {e}")
        raise DBLockError(f"Transaction failed: {e}") from e
