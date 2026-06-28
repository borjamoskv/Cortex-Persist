# [C5-REAL] Exergy-Maximized
"""
PostgreSQL Connection Adapter.

Bridges PostgreSQL connection and query syntax to match the SQLite
cursor-like execution API expected by CortexEngine.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("cortex.db.postgres_adapter")


class PostgresCursorAdapter:
    """Mock SQLite cursor to return results in expected format."""

    def __init__(self, rows: list[Any] | None, lastrowid: int | None = None):
        self._rows = rows or []
        self._idx = 0
        self.lastrowid = lastrowid

    async def fetchone(self) -> Any | None:
        if self._idx < len(self._rows):
            row = self._rows[self._idx]
            self._idx += 1
            if isinstance(row, dict):
                # SQLite cursor fetchone returns tuple
                return tuple(row.values())
            elif hasattr(row, "values"):
                # Record type from asyncpg
                return tuple(row.values())
            elif isinstance(row, tuple):
                return row
            return (row,)
        return None

    async def fetchall(self) -> list[Any]:
        res = []
        while True:
            row = await self.fetchone()
            if row is None:
                break
            res.append(row)
        return res

    async def __aenter__(self) -> PostgresCursorAdapter:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def close(self) -> None:
        pass


class PostgresCursorContext:
    """Provides support for both `await conn.execute(...)` and `async with conn.execute(...)`."""

    def __init__(self, conn: PostgresConnectionAdapter, sql: str, params: tuple[Any, ...]):
        self._conn = conn
        self._sql = sql
        self._params = params
        self._cursor: PostgresCursorAdapter | None = None

    async def _execute(self) -> PostgresCursorAdapter:
        if self._cursor is None:
            self._cursor = await self._conn._execute_internal(self._sql, self._params)
        return self._cursor

    async def __aenter__(self) -> PostgresCursorAdapter:
        return await self._execute()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def __await__(self) -> Any:
        return self._execute().__await__()


class PostgresConnectionAdapter:
    """Wraps asyncpg connection or pool to match the aiosqlite interface."""

    def __init__(self, pg_conn_or_pool: Any, pool: Any = None):
        self._pg_conn_or_pool = pg_conn_or_pool
        self._acquired_conn: Any = None
        self._pool = pool
        self._in_transaction = False

    @property
    def in_transaction(self) -> bool:
        try:
            conn = self._get_active_conn()
            if hasattr(conn, "is_in_transaction"):
                return bool(conn.is_in_transaction())
        except (ValueError, TypeError, OSError, KeyError):
            pass
        return self._in_transaction

    async def __aenter__(self) -> PostgresConnectionAdapter:
        if hasattr(self._pg_conn_or_pool, "acquire") and not self._acquired_conn:
            self._acquired_conn = await self._pg_conn_or_pool.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._acquired_conn:
            if hasattr(self._pg_conn_or_pool, "release"):
                await self._pg_conn_or_pool.release(self._acquired_conn)
            else:
                await self._acquired_conn.close()
            self._acquired_conn = None

    def _get_active_conn(self) -> Any:
        conn = self._acquired_conn
        if conn:
            if isinstance(conn, PostgresConnectionAdapter):
                return conn._get_active_conn()
            return conn
        if hasattr(self._pg_conn_or_pool, "fetch"):
            return self._pg_conn_or_pool
        raise RuntimeError("No active connection available in adapter")

    async def fetch(self, sql: str, *args: Any) -> list[Any]:
        sql = self.translate_sqlite_to_pg(sql)
        pg_sql, pg_params = self._translate_params(sql, args)
        conn = self._get_active_conn()
        res: list[Any] = await conn.fetch(pg_sql, *pg_params)
        return res

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        sql = self.translate_sqlite_to_pg(sql)
        pg_sql, pg_params = self._translate_params(sql, args)
        conn = self._get_active_conn()
        return await conn.fetchrow(pg_sql, *pg_params)

    async def fetchval(self, sql: str, *args: Any) -> Any:
        sql = self.translate_sqlite_to_pg(sql)
        pg_sql, pg_params = self._translate_params(sql, args)
        conn = self._get_active_conn()
        return await conn.fetchval(pg_sql, *pg_params)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> PostgresCursorContext:
        return PostgresCursorContext(self, sql, params)

    async def _execute_internal(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> PostgresCursorAdapter:
        sql_upper = sql.strip().upper()

        match sql_upper:
            case "BEGIN EXCLUSIVE" | "BEGIN TRANSACTION EXCLUSIVE" | "BEGIN TRANSACTION" | "BEGIN":
                sql = "BEGIN"
                self._in_transaction = True
            case "COMMIT" | "COMMIT TRANSACTION":
                sql = "COMMIT"
                self._in_transaction = False
            case "ROLLBACK" | "ROLLBACK TRANSACTION":
                sql = "ROLLBACK"
                self._in_transaction = False

        if "WAL_CHECKPOINT" in sql_upper:
            return PostgresCursorAdapter([])

        pragma_match = re.match(r"(?i)PRAGMA\s+table_info\((.+?)\)", sql.strip())
        if pragma_match:
            table_name = pragma_match.group(1).strip().strip("'\"`").lower()
            sql = (
                "SELECT 0 as cid, column_name as name, data_type as type, 0 as notnull, "
                "NULL as dflt_value, 0 as pk "
                "FROM information_schema.columns "
                f"WHERE table_name = '{table_name}'"
            )

        if "PRAGMA_PAGE_COUNT" in sql_upper or "PRAGMA_PAGE_SIZE" in sql_upper:
            sql = "SELECT pg_database_size(current_database())"

        # Apply general translation rules
        sql = self.translate_sqlite_to_pg(sql)
        pg_sql, pg_params = self._translate_params(sql, params)

        is_insert = pg_sql.strip().upper().startswith("INSERT")
        if is_insert and "RETURNING" not in pg_sql.upper():
            pg_sql = pg_sql.rstrip().rstrip(";") + " RETURNING id"

        conn = self._get_active_conn()
        try:
            if is_insert:
                row = await conn.fetchrow(pg_sql, *pg_params)
                lastrowid = row["id"] if row else 0
                logger.info(
                    "ADAPTER INSERT: SQL=%s | ROW=%s | lastrowid=%s", pg_sql, row, lastrowid
                )
                return PostgresCursorAdapter([row] if row else [], lastrowid=lastrowid)
            else:
                rows = await conn.fetch(pg_sql, *pg_params)
                return PostgresCursorAdapter(rows)
        except Exception as e:
            logger.error(
                "Postgres execution error: %s | SQL: %s | Params: %s", e, pg_sql, pg_params
            )
            raise

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        if not params_list:
            return
        sql = self.translate_sqlite_to_pg(sql)
        pg_sql, _ = self._translate_params(sql, ())
        conn = self._get_active_conn()
        try:
            await conn.executemany(pg_sql, params_list)
        except Exception as e:
            logger.error("Postgres executemany error: %s | SQL: %s", e, pg_sql)
            raise

    async def executescript(self, script: str) -> None:
        statements = [s.strip() for s in script.split(";") if s.strip()]
        if not statements:
            return
        conn = self._get_active_conn()
        try:
            async with conn.transaction():
                for stmt in statements:
                    translated = self.translate_sqlite_to_pg(stmt)
                    pg_sql, _ = self._translate_params(translated, ())
                    await conn.execute(pg_sql)
        except Exception as e:
            logger.error("Postgres executescript error: %s", e)
            raise

    async def commit(self) -> None:
        conn = self._get_active_conn()
        await conn.execute("COMMIT")

    async def rollback(self) -> None:
        conn = self._get_active_conn()
        await conn.execute("ROLLBACK")

    async def close(self) -> None:
        if self._acquired_conn:
            if hasattr(self._pg_conn_or_pool, "release"):
                await self._pg_conn_or_pool.release(self._acquired_conn)
            else:
                await self._acquired_conn.close()
            self._acquired_conn = None

    @staticmethod
    def translate_sqlite_to_pg(sql: str) -> str:
        # 1. Translate INSERT OR IGNORE INTO
        if "INSERT OR IGNORE INTO" in sql.upper():
            sql = re.sub(r"(?i)INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql)
            if "ON CONFLICT" not in sql.upper():
                sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

        # 2. Translate datetime('now') -> NOW()
        sql = re.sub(r"(?i)datetime\('now'\)", "NOW()", sql)

        # 3. Translate julianday('now') - julianday(...) -> EXTRACT(EPOCH FROM (NOW() - ...)) / 86400.0
        sql = re.sub(
            r"(?i)julianday\('now'\)\s*-\s*julianday\((.+?)\)",
            r"(EXTRACT(EPOCH FROM (NOW() - \1)) / 86400.0)",
            sql,
        )

        # 4. Translate json_extract(metadata/meta, '$.parent_decision_id') -> (meta->>'parent_decision_id')::bigint
        sql = re.sub(
            r"(?i)\bjson_extract\((f\.)?metadata,\s*'\$\.parent_decision_id'\)",
            r"((\1meta->>'parent_decision_id')::bigint)",
            sql,
        )
        sql = re.sub(
            r"(?i)\bjson_extract\((f\.)?meta,\s*'\$\.parent_decision_id'\)",
            r"((\1meta->>'parent_decision_id')::bigint)",
            sql,
        )

        # 5. Translate general json_extract(f.metadata, '$.consensus_score') -> (f.meta->>'consensus_score')
        sql = re.sub(
            r"(?i)\bjson_extract\((f\.)?metadata,\s*'\$\.(.+?)'\)", r"(\1meta->>'\2')", sql
        )
        sql = re.sub(r"(?i)\bjson_extract\((f\.)?meta,\s*'\$\.(.+?)'\)", r"(\1meta->>'\2')", sql)

        # 6. Translate f.metadata/metadata to f.meta/meta
        sql = re.sub(r"(?i)\bf\.metadata\b", "f.meta", sql)
        sql = re.sub(r"(?i)\bmetadata\b", "meta", sql)

        return sql

    @staticmethod
    def _translate_params(sql: str, params: tuple[Any, ...] = ()) -> tuple[str, tuple[Any, ...]]:
        if "?" not in sql:
            return sql, params
        parts = []
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


class PostgresAcquireContext:
    """Context manager and awaitable for acquiring connections from PostgresPoolAdapter."""

    def __init__(self, pool: PostgresPoolAdapter):
        self._pool = pool
        self._conn: Any = None
        self._acq_ctx = pool._raw_pool.acquire()

    async def __aenter__(self) -> PostgresConnectionAdapter:
        self._conn = await self._acq_ctx.__aenter__()
        return PostgresConnectionAdapter(self._conn, pool=self._pool)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._acq_ctx.__aexit__(exc_type, exc_val, exc_tb)
        self._conn = None

    def __await__(self) -> Any:
        async def _acquire() -> PostgresConnectionAdapter:
            conn = await self._acq_ctx
            return PostgresConnectionAdapter(conn, pool=self._pool)

        return _acquire().__await__()


class PostgresPoolAdapter:
    """Wraps asyncpg.Pool to provide SQLite-compatible connections and cursors."""

    def __init__(self, raw_pool: Any):
        self._raw_pool = raw_pool

    def acquire(self) -> PostgresAcquireContext:
        return PostgresAcquireContext(self)

    async def release(self, conn: Any) -> None:
        if isinstance(conn, PostgresConnectionAdapter):
            raw_conn = conn._pg_conn_or_pool
            await self._raw_pool.release(raw_conn)
        else:
            await self._raw_pool.release(conn)

    async def close(self) -> None:
        await self._raw_pool.close()
