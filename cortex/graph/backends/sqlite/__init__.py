"""SQLite Graph Backend Package."""

import logging

import aiosqlite

from ..base import GraphBackend
from .algorithms import SQLiteAlgorithmsMixin
from .query import SQLiteQueryMixin
from .store import SQLiteStoreMixin

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
