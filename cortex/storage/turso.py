"""
CORTEX v5.1 — Turso (libSQL) Cloud Backend.

Sovereign-grade cloud storage backend using libSQL.
Optimized for edge performance with transactional batching and
resilient connection management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Final

logger = logging.getLogger("cortex.storage.turso")

# Threshold for "slow" queries in milliseconds
SLOW_QUERY_THRESHOLD_MS: Final[int] = 500


class TursoBackend:
    """Cloud storage backend using Turso (libSQL).

    Turso provides SQLite at the edge, offering high-availability
    and low-latency reads via replication.
    """

    def __init__(self, url: str, auth_token: str):
        self.url: Final[str] = url
        self.auth_token: Final[str] = auth_token
        self._conn: Any = None
        self._libsql: Any = None

    async def connect(self) -> None:
        """Establish connection to Turso with JIT dependency loading."""
        if self._conn:
            return

        try:
            import libsql_experimental as libsql

            self._libsql = libsql
        except ImportError as exc:
            logger.critical("Sovereign Failure: libsql-experimental not installed.")
            raise RuntimeError(
                "libsql-experimental required for Turso. Run: pip install libsql-experimental"
            ) from exc

        logger.info("I18N: Initializing Turso Edge connection to %s", self.url)
        try:
            self._conn = await asyncio.to_thread(
                libsql.connect, self.url, auth_token=self.auth_token
            )
            logger.info("Turso: Connection established successfully.")
        except Exception as e:
            logger.error("Turso: Failed to connect: %s", e)
            raise

    def _ensure_conn(self):
        if self._conn is None:
            raise RuntimeError("TursoBackend not connected. Call connect() first.")

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute SQL with performance tracking and error enrichment."""
        self._ensure_conn()
        start_ts = time.perf_counter()
        try:
            cursor = await asyncio.to_thread(self._conn.execute, sql, params)

            elapsed_ms = (time.perf_counter() - start_ts) * 1000
            if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.warning("Turso Slow Query (%.2fms): %s", elapsed_ms, sql[:100])

            if cursor.description is None:
                return []

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception as e:
            logger.error("Turso Query Error: %s | Query: %s", e, sql[:500])
            raise

    async def execute_insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute INSERT and return lastrowid with atomic commit."""
        self._ensure_conn()
        try:
            # We wrap in a thread because libsql-experimental is largely blocking/threaded
            def _insert():
                cursor = self._conn.execute(sql, params)
                self._conn.commit()
                return cursor.lastrowid or 0

            return await asyncio.to_thread(_insert)
        except Exception as e:
            logger.error("Turso Insert Error: %s", e)
            raise

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute batch parameters within a single transactional block."""
        self._ensure_conn()
        if not params_list:
            return

        try:

            def _exec_many() -> None:
                # Using a manual batch transaction for reliability
                # Note: Newer libsql versions support .batch() for even better perf
                self._conn.execute("BEGIN TRANSACTION")
                try:
                    for params in params_list:
                        self._conn.execute(sql, params)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

            await asyncio.to_thread(_exec_many)
        except Exception as e:
            logger.error("Turso Batch Error (size=%d): %s", len(params_list), e)
            raise

    async def executescript(self, script: str) -> None:
        """Execute multi-statement script safely."""
        self._ensure_conn()
        statements = [s.strip() for s in script.split(";") if s.strip()]
        if not statements:
            return

        try:

            def _exec_script() -> None:
                self._conn.execute("BEGIN TRANSACTION")
                try:
                    for stmt in statements:
                        self._conn.execute(stmt)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

            await asyncio.to_thread(_exec_script)
        except Exception as e:
            logger.error("Turso Script Error (%d stmts): %s", len(statements), e)
            raise

    async def commit(self) -> None:
        """Commit current transaction."""
        self._ensure_conn()
        await asyncio.to_thread(self._conn.commit)

    async def close(self) -> None:
        """Safe connection termination."""
        if self._conn:
            try:
                await asyncio.to_thread(self._conn.close)
                logger.debug("Turso: Connection closed cleanly.")
            except Exception as e:
                logger.warning("Turso: Unclean disconnect: %s", e)
            finally:
                self._conn = None

    async def health_check(self) -> bool:
        """Verify cloud connectivity."""
        try:
            result = await self.execute("SELECT 1 AS ok")
            return len(result) > 0 and result[0].get("ok") == 1
        except Exception:
            return False

    @staticmethod
    def tenant_db_url(base_url: str, tenant_id: str) -> str:
        """
        Generate a per-tenant database URL.
        Example: libsql://cortex.turso.io + alice -> libsql://cortex-alice.turso.io
        """
        if "://" in base_url:
            protocol, rest = base_url.split("://", 1)
            parts = rest.split(".", 1)
            if len(parts) == 2:
                # Injection of tenant suffix for standard Turso naming schemes
                return f"{protocol}://{parts[0]}-{tenant_id}.{parts[1]}"

        return f"{base_url}-{tenant_id}"

    def __repr__(self) -> str:
        return f"<TursoBackend url={self.url!r} connected={self._conn is not None}>"
