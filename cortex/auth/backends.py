# [C5-REAL] Exergy-Maximized
"""
Authentication Backends.

Decouples authentication storage from the core AuthManager logic.
Supports SQLite (Local v5) and distributed cloud backends (v6).
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeAlias

import aiosqlite

if TYPE_CHECKING:
    import asyncpg  # pyright: ignore[reportMissingImports]

KeyData: TypeAlias = dict[str, Any]
KeyID: TypeAlias = int | str

logger = logging.getLogger(__name__)


class BaseAuthBackend(ABC):
    """Abstract base class for CORTEX authentication backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage schema (e.g., create tables)."""

    @abstractmethod
    async def get_key_by_hash(self, key_hash: str) -> KeyData | None:
        """Retrieve an active API key by its hash."""

    @abstractmethod
    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
        key_hash_argon2: str | None = None,
        hash_algo: str = "sha256",
    ) -> int:
        """Store a new API key. Returns the backend-specific unique ID."""

    @abstractmethod
    async def list_keys(self, tenant_id: str | None = None) -> list[KeyData]:
        """List API keys, optionally filtered by tenant."""

    @abstractmethod
    async def revoke_key(self, key_id: KeyID) -> bool:
        """Revoke (deactivate) an API key."""

    @abstractmethod
    async def update_last_used(self, key_id: KeyID) -> None:
        """Update the last_used timestamp for a key."""

    @abstractmethod
    async def get_key_candidates(self, key_prefix: str) -> list[KeyData]:
        """Retrieve active API keys matching a prefix (for Argon2id validation)."""

    @abstractmethod
    async def migrate_key_to_argon2(self, key_id: KeyID, key_hash_argon2: str) -> None:
        """Migrate a key hash to Argon2id and update hash_algo."""


class SQLiteAuthBackend(BaseAuthBackend):
    """Async-first SQLite backend for CORTEX.

    Uses aiosqlite to prevent event loop blocking.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA
        from cortex.database.core import causal_write

        conn = await self._get_conn_async()
        try:
            with causal_write(conn):
                await conn.executescript(AUTH_SCHEMA)
                # Migration
                try:
                    await conn.execute("ALTER TABLE api_keys ADD COLUMN key_hash_argon2 TEXT")
                    await conn.execute(
                        "ALTER TABLE api_keys ADD COLUMN hash_algo TEXT NOT NULL DEFAULT 'sha256'"
                    )
                    await conn.execute("ALTER TABLE api_keys ADD COLUMN migrated_at TEXT")
                except aiosqlite.OperationalError:
                    pass  # Columns already exist
                await conn.commit()
        finally:
            await conn.close()

    async def _get_conn_async(self) -> aiosqlite.Connection:
        from cortex.database.core import connect_async

        return await connect_async(self.db_path)

    async def get_key_by_hash(self, key_hash: str) -> KeyData | None:
        conn = await self._get_conn_async()
        try:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        finally:
            await conn.close()

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
        key_hash_argon2: str | None = None,
        hash_algo: str = "sha256",
    ) -> int:
        from cortex.auth import SQL_INSERT_KEY
        from cortex.database.core import causal_write

        args = (
            name,
            key_hash,
            key_prefix,
            tenant_id,
            role,
            json.dumps(permissions),
            rate_limit,
            key_hash_argon2,
            hash_algo,
        )
        conn = await self._get_conn_async()
        try:
            with causal_write(conn):
                cursor = await conn.execute(SQL_INSERT_KEY, args)
                await conn.commit()
                return cursor.lastrowid  # type: ignore[reportReturnType]
        finally:
            await conn.close()

    async def list_keys(self, tenant_id: str | None = None) -> list[KeyData]:
        conn = await self._get_conn_async()
        try:
            conn.row_factory = aiosqlite.Row
            if tenant_id:
                cursor = await conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cursor = await conn.execute("SELECT * FROM api_keys ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def revoke_key(self, key_id: KeyID) -> bool:
        from cortex.database.core import causal_write

        conn = await self._get_conn_async()
        try:
            with causal_write(conn):
                cursor = await conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
                await conn.commit()
                return cursor.rowcount > 0
        finally:
            await conn.close()

    async def update_last_used(self, key_id: KeyID) -> None:
        from datetime import datetime, timezone

        from cortex.database.core import causal_write

        conn = await self._get_conn_async()
        try:
            with causal_write(conn):
                await conn.execute(
                    "UPDATE api_keys SET last_used = ? WHERE id = ?",
                    (datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(), key_id),
                )
                await conn.commit()
        except (aiosqlite.Error, OSError) as e:
            logger.debug("Could not update last_used (async): %s", e)
        finally:
            await conn.close()

    async def get_key_candidates(self, key_prefix: str) -> list[KeyData]:
        conn = await self._get_conn_async()
        try:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM api_keys WHERE key_prefix = ? AND is_active = 1",
                (key_prefix,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def migrate_key_to_argon2(self, key_id: KeyID, key_hash_argon2: str) -> None:
        from datetime import datetime, timezone

        from cortex.database.core import causal_write

        conn = await self._get_conn_async()
        try:
            with causal_write(conn):
                await conn.execute(
                    "UPDATE api_keys SET key_hash_argon2 = ?, hash_algo = 'argon2id', migrated_at = ? WHERE id = ?",
                    (
                        key_hash_argon2,
                        datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                        key_id,
                    ),
                )
                await conn.commit()
        except (aiosqlite.Error, OSError) as e:
            logger.debug("Could not migrate key (async): %s", e)
        finally:
            await conn.close()


class AlloyDBAuthBackend(BaseAuthBackend):
    """Distributed authentication backend for AlloyDB / PostgreSQL.

    Uses asyncpg for native asynchronous operations.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        import asyncpg  # pyright: ignore[reportMissingImports]

        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn)
        return self._pool  # type: ignore[return-value]

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        # AlloyDB/Postgres uses SERIAL/TEXT instead of INTEGER PRIMARY KEY AUTOINCREMENT
        pg_schema = AUTH_SCHEMA.replace(
            "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
        ).replace("strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", "CURRENT_TIMESTAMP")

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(pg_schema)
            # Migration
            try:
                await conn.execute(
                    "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_hash_argon2 TEXT"
                )
                await conn.execute(
                    "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS hash_algo TEXT NOT NULL DEFAULT 'sha256'"
                )
                await conn.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS migrated_at TEXT")
            except Exception as e:
                logger.debug("AlloyDB columns already exist or error: %s", e)

    async def get_key_by_hash(self, key_hash: str) -> KeyData | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key_hash = $1 AND is_active = 1",
                key_hash,
            )
            return dict(row) if row else None

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
        key_hash_argon2: str | None = None,
        hash_algo: str = "sha256",
    ) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            key_id = await conn.fetchval(
                """
                INSERT INTO api_keys
                    (name, key_hash, key_prefix, tenant_id, role, permissions, rate_limit, key_hash_argon2, hash_algo)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                name,
                key_hash,
                key_prefix,
                tenant_id,
                role,
                json.dumps(permissions),
                rate_limit,
                key_hash_argon2,
                hash_algo,
            )
            return key_id  # type: ignore[no-any-return]

    async def list_keys(self, tenant_id: str | None = None) -> list[KeyData]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(
                    "SELECT * FROM api_keys WHERE tenant_id = $1 ORDER BY id DESC",
                    tenant_id,
                )
            else:
                rows = await conn.fetch("SELECT * FROM api_keys ORDER BY id DESC")
            return [dict(r) for r in rows]

    async def revoke_key(self, key_id: KeyID) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = $1", key_id)
            # res is something like "UPDATE 1"
            return res.endswith("1")

    async def update_last_used(self, key_id: KeyID) -> None:
        from datetime import datetime, timezone

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE api_keys SET last_used = $1 WHERE id = $2",
                datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                key_id,
            )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_key_candidates(self, key_prefix: str) -> list[KeyData]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM api_keys WHERE key_prefix = $1 AND is_active = 1",
                key_prefix,
            )
            return [dict(r) for r in rows]

    async def migrate_key_to_argon2(self, key_id: KeyID, key_hash_argon2: str) -> None:
        from datetime import datetime, timezone

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE api_keys SET key_hash_argon2 = $1, hash_algo = 'argon2id', migrated_at = $2 WHERE id = $3",
                key_hash_argon2,
                datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                key_id,
            )


class TursoAuthBackend(BaseAuthBackend):
    """Distributed authentication backend for Turso / libSQL over HTTP/WebSockets.

    Optimized for Vercel/Serverless deployments using libsql-client.
    """

    def __init__(self, url: str, auth_token: str) -> None:
        self.url = url
        self.auth_token = auth_token
        self._client: Any = None

    async def _get_client(self) -> Any:
        import libsql_client  # pyright: ignore[reportMissingImports]

        if self._client is None:
            self._client = libsql_client.create_client(self.url, auth_token=self.auth_token)
        return self._client

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        client = await self._get_client()
        # Create statements, ignoring empty ones
        statements = [s.strip() for s in AUTH_SCHEMA.split(";") if s.strip()]
        for stmt in statements:
            await client.execute(stmt)

        try:
            await client.execute("ALTER TABLE api_keys ADD COLUMN key_hash_argon2 TEXT")
            await client.execute(
                "ALTER TABLE api_keys ADD COLUMN hash_algo TEXT NOT NULL DEFAULT 'sha256'"
            )
            await client.execute("ALTER TABLE api_keys ADD COLUMN migrated_at TEXT")
        except (ValueError, TypeError, OSError, KeyError):
            pass  # Columns already exist

    async def get_key_by_hash(self, key_hash: str) -> KeyData | None:
        client = await self._get_client()
        res = await client.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1", [key_hash]
        )
        if res.rows:
            return dict(zip(res.columns, res.rows[0], strict=False))
        return None

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
        key_hash_argon2: str | None = None,
        hash_algo: str = "sha256",
    ) -> int:
        from cortex.auth import SQL_INSERT_KEY

        client = await self._get_client()
        args = [
            name,
            key_hash,
            key_prefix,
            tenant_id,
            role,
            json.dumps(permissions),
            rate_limit,
            key_hash_argon2,
            hash_algo,
        ]
        res = await client.execute(SQL_INSERT_KEY, args)
        return res.last_insert_rowid

    async def list_keys(self, tenant_id: str | None = None) -> list[KeyData]:
        client = await self._get_client()
        if tenant_id:
            res = await client.execute(
                "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY id DESC", [tenant_id]
            )
        else:
            res = await client.execute("SELECT * FROM api_keys ORDER BY id DESC")
        return [dict(zip(res.columns, row, strict=False)) for row in res.rows]

    async def revoke_key(self, key_id: KeyID) -> bool:
        client = await self._get_client()
        res = await client.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", [key_id])
        return res.rows_affected > 0

    async def update_last_used(self, key_id: KeyID) -> None:
        from datetime import datetime, timezone

        client = await self._get_client()
        try:
            await client.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                [datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(), key_id],
            )
        except Exception as e:
            logger.debug("Could not update last_used in Turso: %s", e)

    async def close(self) -> None:
        """Close the Turso client."""
        if self._client:
            await self._client.close()
            self._client = None

    async def get_key_candidates(self, key_prefix: str) -> list[KeyData]:
        client = await self._get_client()
        res = await client.execute(
            "SELECT * FROM api_keys WHERE key_prefix = ? AND is_active = 1", [key_prefix]
        )
        return [dict(zip(res.columns, row, strict=False)) for row in res.rows]

    async def migrate_key_to_argon2(self, key_id: KeyID, key_hash_argon2: str) -> None:
        from datetime import datetime, timezone

        client = await self._get_client()
        try:
            await client.execute(
                "UPDATE api_keys SET key_hash_argon2 = ?, hash_algo = 'argon2id', migrated_at = ? WHERE id = ?",
                [
                    key_hash_argon2,
                    datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                    key_id,
                ],
            )
        except Exception as e:
            logger.debug("Could not migrate key in Turso: %s", e)
