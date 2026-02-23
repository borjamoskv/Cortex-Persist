"""
CORTEX v6 — Authentication Backends.

Decouples authentication storage from the core AuthManager logic.
Supports SQLite (Local v5) and distributed cloud backends (v6).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from typing import Any

# We keep the core dataclasses here to avoid circular imports if auth.py uses this
# But for now, let's assume those stay in auth.py and this file imports them if needed.
# Actually, it's better if backends.py doesn't depend on auth.py's internal classes.

logger = logging.getLogger(__name__)


class BaseAuthBackend(ABC):
    """Abstract base class for CORTEX authentication backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage schema (e.g., create tables)."""
        pass

    @abstractmethod
    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        """Retrieve an active API key by its hash."""
        pass

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
    ) -> int:
        """Store a new API key. Returns the backend-specific unique ID."""
        pass

    @abstractmethod
    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """List API keys, optionally filtered by tenant."""
        pass

    @abstractmethod
    async def revoke_key(self, key_id: int | str) -> bool:
        """Revoke (deactivate) an API key."""
        pass

    @abstractmethod
    async def update_last_used(self, key_id: int | str) -> None:
        """Update the last_used timestamp for a key."""
        pass


class SQLiteAuthBackend(BaseAuthBackend):
    """Legacy-compatible SQLite backend for CORTEX v5.0+."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        conn = self._get_conn()
        try:
            conn.executescript(AUTH_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        from cortex.db import connect

        return connect(self.db_path, row_factory=sqlite3.Row)

    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        from cortex.auth import SQL_INSERT_KEY

        args = (name, key_hash, key_prefix, tenant_id, role, json.dumps(permissions), rate_limit)
        conn = self._get_conn()
        try:
            cursor = conn.execute(SQL_INSERT_KEY, args)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._get_conn()
        try:
            if tenant_id:
                rows = conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    async def revoke_key(self, key_id: int | str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    async def update_last_used(self, key_id: int | str) -> None:
        from datetime import datetime, timezone

        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id),
            )
            conn.commit()
        except sqlite3.OperationalError as e:
            logger.debug("Could not update last_used (DB busy: %s), skipping", e)
        finally:
            conn.close()


class AlloyDBAuthBackend(BaseAuthBackend):
    """Distributed authentication backend for AlloyDB / PostgreSQL.

    Uses asyncpg for native asynchronous operations.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool = None

    async def _get_pool(self):
        import asyncpg

        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn)
        return self._pool

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        # AlloyDB/Postgres uses SERIAL/TEXT instead of INTEGER PRIMARY KEY AUTOINCREMENT
        pg_schema = AUTH_SCHEMA.replace(
            "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
        ).replace("strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", "CURRENT_TIMESTAMP")

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(pg_schema)

    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
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
    ) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            key_id = await conn.fetchval(
                """
                INSERT INTO api_keys
                    (name, key_hash, key_prefix, tenant_id, role, permissions, rate_limit)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                name,
                key_hash,
                key_prefix,
                tenant_id,
                role,
                json.dumps(permissions),
                rate_limit,
            )
            return key_id

    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(
                    "SELECT * FROM api_keys WHERE tenant_id = $1 ORDER BY created_at DESC",
                    tenant_id,
                )
            else:
                rows = await conn.fetch("SELECT * FROM api_keys ORDER BY created_at DESC")
            return [dict(r) for r in rows]

    async def revoke_key(self, key_id: int | str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = $1", key_id)
            # res is something like "UPDATE 1"
            return res.endswith("1")

    async def update_last_used(self, key_id: int | str) -> None:
        from datetime import datetime, timezone

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE api_keys SET last_used = $1 WHERE id = $2",
                datetime.now(timezone.utc).isoformat(),
                key_id,
            )

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
