"""Sync base mixin for CortexEngine.

Provides connection management for synchronous operations.
"""

from __future__ import annotations

import logging

import sqlite_vec

__all__ = ["SyncBaseMixin"]

logger = logging.getLogger("cortex")


class SyncBaseMixin:
    """Base mixin for synchronous connection management."""

    def _get_sync_conn(self):
        """Get a raw sqlite3.Connection for sync callers."""
        if not hasattr(self, "_sync_conn") or self._sync_conn is None:
            from cortex.db import connect

            self._sync_conn = connect(str(self._db_path))
            try:
                self._sync_conn.enable_load_extension(True)
                sqlite_vec.load(self._sync_conn)
                self._sync_conn.enable_load_extension(False)
                self._vec_available = True
                logger.debug("sqlite-vec loaded successfully (sync)")
            except (OSError, AttributeError) as e:
                logger.debug("sqlite-vec extension not available (sync): %s", e)
                self._vec_available = False
        return self._sync_conn

    def close_sync(self):
        """Close sync connection."""
        if hasattr(self, "_sync_conn") and self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None
