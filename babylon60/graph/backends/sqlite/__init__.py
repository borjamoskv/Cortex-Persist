# [C5-REAL] Exergy-Maximized

import logging

import aiosqlite
from babylon60.graph.backends.base import GraphBackend
from babylon60.graph.backends.sqlite.algorithms import SQLiteAlgorithmsMixin
from babylon60.graph.backends.sqlite.query import SQLiteQueryMixin
from babylon60.graph.backends.sqlite.store import SQLiteStoreMixin

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
