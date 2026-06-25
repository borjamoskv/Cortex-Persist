# [C5-REAL] Exergy-Maximized

import logging

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

from cortex.graph.backends.base import GraphBackend
from cortex.graph.backends.sqlite.algorithms import SQLiteAlgorithmsMixin
from cortex.graph.backends.sqlite.query import SQLiteQueryMixin
from cortex.graph.backends.sqlite.store import SQLiteStoreMixin

logger = logging.getLogger("cortex.graph.backends")


class SQLiteBackend(SQLiteStoreMixin, SQLiteQueryMixin, SQLiteAlgorithmsMixin, GraphBackend):
    """
    SQLite implementation of GraphBackend.
    Decomposed into mixins for maintainability (Operation TITAN DROP).
    """

    def __init__(self, conn):
        self.conn = conn
        self._is_async = isinstance(conn, aiosqlite.Connection)
        # Mixins don't need explicit init if they just use self.conn,
        # but SQLiteStoreMixin sets self._is_async so we can call it.
        SQLiteStoreMixin.__init__(self, conn)


__all__ = ["SQLiteBackend"]
