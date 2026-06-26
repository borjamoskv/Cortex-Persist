# [C5-REAL] Exergy-Maximized
"""CORTEX Engine - Connection and Schema Initialization Mixin.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite
import sqlite_vec

from cortex.database.core import connect, load_sqlite_vec_async
from cortex.database.schema import get_init_meta
from cortex.migrations.core import run_migrations_async
from cortex.telemetry.metrics import metrics

logger = logging.getLogger("cortex.engine.guards")


class ConnectionMixin:
    """Mixin providing database connection and schema management for CortexEngine."""

    @property
    def _conn_lock(self) -> asyncio.Lock:
        from cortex.utils.locks import get_loop_lock

        return get_loop_lock(self, "conn")

    @property
    def _schema_lock(self) -> asyncio.Lock:
        from cortex.utils.locks import get_loop_lock

        return get_loop_lock(self, "schema")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Proporciona una sesión transaccional (conexión) válida."""
        if hasattr(self, "_pool") and self._pool is not None:  # pyright: ignore[reportAttributeAccessIssue]
            async with self._pool.acquire() as conn:  # pyright: ignore[reportAttributeAccessIssue]
                yield conn
        else:
            conn = await self._get_or_create_conn()
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Provides a transactional context, committing on success or rolling back on error."""
        async with self.session() as conn:
            try:
                await conn.execute("BEGIN")
                yield conn
                await conn.commit()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError):
                await conn.rollback()
                raise

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns the async database connection.
        DEPRECATED: Use 'async with engine.session() as conn:' instead.
        """
        warnings.warn(
            "get_conn() is deprecated. Use session() context manager.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self._get_or_create_conn()

    async def _get_conn(self) -> aiosqlite.Connection:
        """Internal helper for connection acquisition (deprecated alias)."""
        return await self._get_or_create_conn()

    async def _get_or_create_conn(self) -> aiosqlite.Connection:
        """Internal helper for connection acquisition."""
        async with self._conn_lock:
            if not hasattr(self, "_conns_by_loop"):
                self._conns_by_loop = {}
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            conn = self._conns_by_loop.get(current_loop)

            if conn is not None:
                if (
                    conn._cortex_loop is None
                    or conn._cortex_loop.is_closed()
                    or not conn._running
                    or not conn._thread.is_alive()
                ):
                    try:
                        await conn.close()
                    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                        logger.warning("Suppressed exception: %s", exc)
                    self._conns_by_loop.pop(current_loop, None)
                    conn = None
                else:
                    return conn

            from cortex.database.core import connect_async

            conn = await connect_async(str(self._db_path))  # pyright: ignore[reportAttributeAccessIssue]
            try:
                conn._cortex_loop = asyncio.get_running_loop()  # pyright: ignore[reportAttributeAccessIssue]
            except RuntimeError:
                conn._cortex_loop = None  # pyright: ignore[reportAttributeAccessIssue]

            self._conns_by_loop[current_loop] = conn

            self._vec_available = await load_sqlite_vec_async(conn)
            await self._ensure_schema_ready(conn)
            if not getattr(self, "_memory_ready", False):
                with getattr(self, "_thread_init_lock", None) or threading.Lock():
                    if not getattr(self, "_memory_ready", False):
                        await self._init_memory_subsystem(self._db_path, conn)  # pyright: ignore[reportAttributeAccessIssue]
            return conn

    async def _ensure_schema_ready(self, conn: aiosqlite.Connection) -> None:
        """Bootstrap the base schema once per engine instance."""
        if self._schema_ready:
            return
        with getattr(self, "_thread_init_lock", None) or threading.Lock():
            if self._schema_ready:
                return

            # Autorizar migraciones físicamente
            if hasattr(conn._conn, "authorize_causal_writes"):
                conn._conn.authorize_causal_writes()

            try:
                await run_migrations_async(conn)
                for k, v in get_init_meta():
                    await conn.execute(
                        "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                        (k, v),
                    )
                await conn.commit()

                # Dynamic tenant isolation salt resolution
                cursor = await conn.execute(
                    "SELECT value FROM cortex_meta WHERE key = 'tenant_isolation_salt'"
                )
                row = await cursor.fetchone()
                if row:
                    import cortex.core.config as config

                    config.HKDF_SALT = row[0]
                else:
                    import cortex.core.config as config

                    # Store the default config salt in the DB if not present
                    await conn.execute(
                        "INSERT INTO cortex_meta (key, value) VALUES ('tenant_isolation_salt', ?)",
                        (config.HKDF_SALT,),
                    )
                    await conn.commit()
            finally:
                if hasattr(conn._conn, "revoke_causal_writes"):
                    conn._conn.revoke_causal_writes()

            # Query dynamic salt if present to reload config dynamically
            try:
                async with conn.execute(
                    "SELECT value FROM cortex_meta WHERE key = ?", ("tenant_isolation_salt",)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        import cortex.core.config as config

                        config.HKDF_SALT = row[0]
                        config._cfg.HKDF_SALT = row[0]
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.warning("Failed to load tenant_isolation_salt: %s", e)

            # Ensure we do not leave a read transaction open on the connection
            try:
                await conn.commit()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError):
                pass

            if self._ledger is None:
                from cortex.ledger import ImmutableLedger

                self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
            self._schema_ready = True

    async def _get_or_create_ledger(self):
        """Return the transaction ledger, initializing it on demand."""
        conn = await self._get_or_create_conn()
        await self._ensure_schema_ready(conn)
        if self._ledger is None:
            from cortex.ledger import ImmutableLedger

            self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
        return self._ledger

    def get_connection(self) -> aiosqlite.Connection:
        """Synchronous wrapper for internal connection access."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        conn = getattr(self, "_conns_by_loop", {}).get(loop)
        if conn is None:
            raise RuntimeError("Connection not initialized. Call session() first.")
        return conn

    def _get_sync_conn(self):
        """Devuelve una conexión síncrona para procesos bloqueantes."""

        conn = connect(str(self._db_path), row_factory=sqlite3.Row)  # pyright: ignore[reportAttributeAccessIssue]
        try:
            conn.enable_load_extension(True)
            conn.load_extension(sqlite_vec.loadable_path())
            conn.enable_load_extension(False)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            logger.warning("Suppressed exception: %s", exc)
        if not hasattr(self, "_sync_conns"):
            self._sync_conns = []
        self._sync_conns.append(conn)
        return conn

    async def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        conn = await self._get_or_create_conn()
        await self._ensure_schema_ready(conn)
        await self._persistence.start()  # pyright: ignore[reportAttributeAccessIssue]
        metrics.set_engine(self)
        logger.info("CORTEX database initialized (async) at %s", self._db_path)  # pyright: ignore[reportAttributeAccessIssue]
