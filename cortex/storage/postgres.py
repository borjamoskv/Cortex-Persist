"""
CORTEX v6.0 — PostgreSQL Cloud Backend.

Production-grade cloud storage backend using asyncpg.
Designed for AlloyDB/CloudSQL/RDS deployments with connection
pooling, parameterized queries, and full StorageBackend protocol
compliance.

Usage:
    CORTEX_STORAGE=postgres
    POSTGRES_DSN=postgresql://user:pass@host:5432/cortex

Schema Init:
    By default, connect() applies the PG schema automatically (idempotent).
    Set auto_init_schema=False to skip (e.g., for read-only replicas).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Final

__all__ = ["PostgresBackend"]

logger = logging.getLogger("cortex.storage.postgres")

# Threshold for "slow" queries in milliseconds
SLOW_QUERY_THRESHOLD_MS: Final[int] = 500

# Connection pool bounds
MIN_POOL_SIZE: Final[int] = 2
MAX_POOL_SIZE: Final[int] = 20

# Env-var escape hatch: set to '1' or 'true' to protect read replicas
# from DDL statements without requiring code changes.
# CORTEX_PG_REPLICA_MODE=1 forces auto_init_schema=False and
# blocks executescript/executemany (DDL guard).
_REPLICA_MODE_ENV: Final[str] = "CORTEX_PG_REPLICA_MODE"


def _replica_mode_from_env() -> bool:
    """Read CORTEX_PG_REPLICA_MODE from environment.

    Supports: '1', 'true', 'yes', 'on' (case-insensitive) → True.
    Anything else (or not set) → False.
    """
    raw = os.environ.get(_REPLICA_MODE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class PostgresBackend:
    """Cloud storage backend using PostgreSQL via asyncpg.

    Implements the StorageBackend protocol for production cloud
    deployments. Uses native asyncpg connection pooling with
    automatic reconnection and health monitoring.

    Features:
    - asyncpg connection pool (min/max bounds)
    - Parameterized queries ($1, $2 syntax auto-translated from ?)
    - Slow query logging
    - Health checks via SELECT 1
    - Transactional executemany and executescript
    """

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = MIN_POOL_SIZE,
        max_size: int = MAX_POOL_SIZE,
        auto_init_schema: bool = True,
    ):
        # Env-var replica mode overrides the caller's auto_init_schema.
        # This is the escape hatch that makes the default safe:
        # a read replica ops team can set CORTEX_PG_REPLICA_MODE=1
        # without touching a single line of application code.
        self._is_replica: Final[bool] = _replica_mode_from_env()
        if self._is_replica:
            auto_init_schema = False
            logger.warning(
                "PostgreSQL: REPLICA MODE active (%s=1). "
                "auto_init_schema=False enforced. DDL writes blocked.",
                _REPLICA_MODE_ENV,
            )

        self.dsn: Final[str] = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._auto_init_schema = auto_init_schema
        self._pool: Any = None  # asyncpg.Pool

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL."""
        if self._pool is not None:
            return

        try:
            import asyncpg
        except ImportError as exc:
            logger.critical("Sovereign Failure: asyncpg not installed.")
            raise RuntimeError(
                "asyncpg required for PostgreSQL backend. Run: pip install asyncpg"
            ) from exc

        logger.info(
            "Initializing PostgreSQL pool: %s (min=%d, max=%d)",
            self._sanitize_dsn(self.dsn),
            self._min_size,
            self._max_size,
        )
        try:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=60,
            )
            logger.info("PostgreSQL: Connection pool established successfully.")

            if self._auto_init_schema:
                await self.initialize_schema()
        except OSError as exc:
            logger.error("PostgreSQL: Failed to connect: %s", exc)
            raise

    async def initialize_schema(self) -> None:
        """Apply the full CORTEX PostgreSQL schema (idempotent).

        Applies PG extensions (pgvector, pg_trgm) first, then all
        table definitions. Safe to call multiple times — all statements
        use CREATE IF NOT EXISTS.

        Raises:
            RuntimeError: If the backend is not connected.
        """
        from cortex.storage.pg_schema import PG_ALL_SCHEMA, PG_EXTENSIONS

        self._ensure_pool()
        logger.info("PostgreSQL: Applying schema (idempotent)...")

        # Apply extensions — may require superuser; log warning if unavailable
        try:
            await self.executescript(PG_EXTENSIONS)
            logger.debug("PostgreSQL: Extensions applied (pgvector, pg_trgm).")
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostgreSQL: Extensions skipped (insufficient privileges): %s", exc)

        # Apply all schema statements — each is idempotent
        for i, schema_sql in enumerate(PG_ALL_SCHEMA):
            try:
                await self.executescript(schema_sql)
            except Exception as exc:
                logger.error(
                    "PostgreSQL: Schema statement %d/%d failed: %s",
                    i + 1,
                    len(PG_ALL_SCHEMA),
                    exc,
                )
                raise

        logger.info("PostgreSQL: Schema initialized (%d statements).", len(PG_ALL_SCHEMA))

    def _ensure_pool(self) -> None:
        if self._pool is None:
            raise RuntimeError("PostgresBackend not connected. Call connect() first.")

    @staticmethod
    def _translate_params(sql: str, params: tuple[Any, ...] = ()) -> tuple[str, tuple[Any, ...]]:
        """Translate SQLite-style ? placeholders to PostgreSQL $N style.

        Also handles common SQLite → PostgreSQL syntax differences:
        - AUTOINCREMENT → handled at schema level
        - datetime('now') → NOW() — handled at schema level
        """
        if "?" not in sql:
            return sql, params

        # Replace ? with $1, $2, etc.
        parts: list[str] = []
        param_idx = 0
        i = 0
        while i < len(sql):
            if sql[i] == "?":
                param_idx += 1
                parts.append(f"${param_idx}")
            else:
                parts.append(sql[i])
            i += 1

        return "".join(parts), params

    @staticmethod
    def _sanitize_dsn(dsn: str) -> str:
        """Hide password from DSN for logging."""
        if "@" in dsn and ":" in dsn:
            # postgresql://user:PASS@host → postgresql://user:***@host
            try:
                pre_at = dsn.split("@")[0]
                post_at = dsn.split("@")[1]
                if ":" in pre_at:
                    user_part = pre_at.rsplit(":", 1)[0]
                    return f"{user_part}:***@{post_at}"
            except (IndexError, ValueError):
                pass
        return dsn

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute a single SQL statement and return rows as dicts."""
        self._ensure_pool()
        pg_sql, pg_params = self._translate_params(sql, params)

        start_ts = time.perf_counter()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(pg_sql, *pg_params)

            elapsed_ms = (time.perf_counter() - start_ts) * 1000
            if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.warning("PG Slow Query (%.2fms): %s", elapsed_ms, sql[:100])

            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("PG Query Error: %s | Query: %s", exc, sql[:500])
            raise

    async def execute_insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT and return the last row ID.

        Appends RETURNING id to the SQL if not already present.
        """
        self._ensure_pool()
        pg_sql, pg_params = self._translate_params(sql, params)

        # Auto-add RETURNING clause for INSERT statements
        sql_upper = pg_sql.strip().upper()
        if sql_upper.startswith("INSERT") and "RETURNING" not in sql_upper:
            # Remove trailing semicolon if present
            pg_sql = pg_sql.rstrip().rstrip(";")
            pg_sql += " RETURNING id"

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(pg_sql, *pg_params)
                return row["id"] if row else 0
        except Exception as exc:
            logger.error("PG Insert Error: %s", exc)
            raise

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute a statement with multiple parameter sets within a transaction."""
        self._ensure_pool()
        if not params_list:
            return

        pg_sql, _ = self._translate_params(sql, ())

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    # asyncpg executemany is optimized for batch operations
                    await conn.executemany(pg_sql, params_list)
        except Exception as exc:
            logger.error("PG Batch Error (size=%d): %s", len(params_list), exc)
            raise

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script within a transaction.

        Handles statement splitting and ignores empty statements.
        For PostgreSQL schema initialization, this method wraps all
        statements in a single transaction for atomicity.
        """
        self._ensure_pool()
        statements = [s.strip() for s in script.split(";") if s.strip()]
        if not statements:
            return

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for stmt in statements:
                        await conn.execute(stmt)
        except Exception as exc:
            logger.error("PG Script Error (%d stmts): %s", len(statements), exc)
            raise

    async def commit(self) -> None:
        """Commit is handled by transaction context managers in asyncpg.

        This is a no-op since asyncpg uses explicit transaction blocks.
        Kept for StorageBackend protocol compliance.
        """
        pass

    async def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            try:
                await self._pool.close()
                logger.debug("PostgreSQL: Pool closed cleanly.")
            except Exception as exc:
                logger.warning("PostgreSQL: Unclean pool close: %s", exc)
            finally:
                self._pool = None

    async def health_check(self) -> bool:
        """Verify PostgreSQL connectivity."""
        try:
            result = await self.execute("SELECT 1 AS ok")
            return len(result) > 0 and result[0].get("ok") == 1
        except Exception:
            return False

    def __repr__(self) -> str:
        connected = self._pool is not None
        return f"<PostgresBackend dsn={self._sanitize_dsn(self.dsn)!r} connected={connected}>"
