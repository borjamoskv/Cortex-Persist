# [C5-REAL] Exergy-Maximized
"""CORTEX Engine - Connection and Schema Initialization Mixin.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
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
import warnings
from collections.abc import AsyncIterator
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
import sqlite_vec

from babylon60.database.core import connect, load_sqlite_vec_async
from babylon60.database.schema import get_init_meta
from babylon60.migrations.core import run_migrations_async
from babylon60.telemetry.metrics import metrics

logger = logging.getLogger("babylon60.engine.guards")


class ConnectionMixin:
    """Mixin providing database connection and schema management for CortexEngine."""

    @property
    def _conn_lock(self) -> asyncio.Lock:
        from babylon60.utils.locks import get_loop_lock

        return get_loop_lock(self, "conn")

    @property
    def _schema_lock(self) -> asyncio.Lock:
        from babylon60.utils.locks import get_loop_lock

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
        """Provides a transactional context, committing on success or rolling back on error.

        Uses BEGIN IMMEDIATE to acquire the RESERVED lock at transaction start,
        preventing the read-modify-write race (Issue #464) if callers perform
        hash-chain or ledger mutations through this context manager.
        """
        async with self.session() as conn:
            try:
                await conn.execute("BEGIN IMMEDIATE")
                yield conn
                await conn.commit()
            except Exception:
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
                    except Exception as exc:
                        logger.warning("Suppressed exception: %s", exc)
                    self._conns_by_loop.pop(current_loop, None)
                    conn = None
                else:
                    return conn

            from babylon60.database.core import connect_async

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
                import babylon60.core.config as config
                config.HKDF_SALT = row[0]
            else:
                import babylon60.core.config as config
                # Store the default config salt in the DB if not present
                await conn.execute(
                    "INSERT INTO cortex_meta (key, value) VALUES ('tenant_isolation_salt', ?)",
                    (config.HKDF_SALT,),
                )
                await conn.commit()
            
            # Query dynamic salt if present to reload config dynamically
            try:
                async with conn.execute(
                    "SELECT value FROM cortex_meta WHERE key = ?", ("tenant_isolation_salt",)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        import babylon60.core.config as config
                        config.HKDF_SALT = row[0]
                        config._cfg.HKDF_SALT = row[0]
            except Exception as e:
                logger.warning("Failed to load tenant_isolation_salt: %s", e)

            # Ensure we do not leave a read transaction open on the connection
            try:
                await conn.commit()
            except Exception:
                pass

            if self._ledger is None:
                from babylon60.ledger import ImmutableLedger

                self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
            self._schema_ready = True


    async def _get_or_create_ledger(self):
        """Return the transaction ledger, initializing it on demand."""
        conn = await self._get_or_create_conn()
        await self._ensure_schema_ready(conn)
        if self._ledger is None:
            from babylon60.ledger import ImmutableLedger

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
        except Exception as exc:
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
