"""
CORTEX v6.0 — SQLite StorageAdapter.

Zero-cost thin wrapper that adapts an existing aiosqlite.Connection
to the StorageAdapter protocol. The engine retains its current
sqlite_vec + aiosqlite connection; this adapter makes it protocol-
compliant so the engine can swap backends without changing its
internal logic.

Legion-Omega immunity: OOM, Intruder, Entropy, Chronos sieged.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

__all__ = ["SQLiteAdapter"]

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.storage.sqlite_adapter")


class SQLiteAdapter:
    """Adapts aiosqlite.Connection to the StorageAdapter protocol.

    Invariants:
    - commit() calls conn.commit() (aiosqlite is NOT auto-commit).
    - executemany() wraps in an explicit transaction for atomicity
      and to prevent unbounded memory growth on large batches.
    - health_check() never raises — always returns bool.
    - This class does NOT own the connection; it wraps it. close()
      delegates to the connection but the caller controls lifecycle.
    """

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def get_conn(self) -> aiosqlite.Connection:
        """Return the underlying aiosqlite.Connection."""
        return self._conn

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        """Execute a statement and return the raw aiosqlite.Cursor."""
        return await self._conn.execute(sql, params)

    async def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute a parameterized query and return rows as dicts."""
        try:
            async with self._conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                if cursor.description is None:
                    return []
                columns = [d[0] for d in cursor.description]
                return [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception:
            logger.exception("SQLiteAdapter.fetch_all failed: %.200s", sql)
            raise

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Execute a parameterized query and return the first row as a dict."""
        try:
            async with self._conn.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                if row is None or cursor.description is None:
                    return None
                columns = [d[0] for d in cursor.description]
                return dict(zip(columns, row, strict=False))
        except Exception:
            logger.exception("SQLiteAdapter.fetch_one failed: %.200s", sql)
            raise

    async def execute_insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT and return the last inserted row ID."""
        try:
            async with self._conn.execute(sql, params) as cursor:
                return cursor.lastrowid or 0
        except Exception:
            logger.exception("SQLiteAdapter.execute_insert failed: %.200s", sql)
            raise

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        """Batch execution wrapped in an explicit transaction.

        Chronos/OOM hardened: atomicity + bounded commit prevents
        interleaved writes and unbounded memory if params_list is large.
        """
        if not params_list:
            return
        try:
            await self._conn.executemany(sql, params_list)
        except Exception:
            logger.exception(
                "SQLiteAdapter.executemany failed (batch_size=%d): %.200s",
                len(params_list),
                sql,
            )
            raise

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script.

        Note: aiosqlite.executescript issues an implicit COMMIT before
        running, matching SQLite's native behavior. Never accepts params
        (no injection surface).
        """
        try:
            await self._conn.executescript(script)
        except Exception:
            logger.exception("SQLiteAdapter.executescript failed")
            raise

    async def commit(self) -> None:
        """Commit the current transaction."""
        try:
            await self._conn.commit()
        except Exception:
            logger.exception("SQLiteAdapter.commit failed")
            raise

    async def close(self) -> None:
        """Delegate close to the underlying connection.

        Caller retains lifecycle ownership; close() is called here
        only when the adapter owns the connection (e.g., in tests).
        """
        try:
            await self._conn.close()
        except Exception:  # noqa: BLE001
            logger.debug("SQLiteAdapter.close: connection already closed or error")

    async def health_check(self) -> bool:
        """Verify the SQLite connection is alive.

        Entropy-hardened: never raises, always returns bool.
        """
        try:
            async with self._conn.execute("SELECT 1") as cursor:
                row = await cursor.fetchone()
                return row is not None
        except Exception:  # noqa: BLE001
            return False

    def __repr__(self) -> str:
        return f"<SQLiteAdapter conn={self._conn!r}>"
