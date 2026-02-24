"""Autonomous Cloud Edge Synchronization Monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

from cortex import config
from cortex.daemon.models import CloudSyncAlert
from cortex.storage.turso import TursoBackend

logger = logging.getLogger("moskv-daemon")


class CloudSyncMonitor:
    """Asynchronously syncs local transactions to the Turso Edge Cloud.
    Operates as a pure async queue processor, removing write latency from the local DB.
    """

    def __init__(
        self,
        interval_seconds: int = 15,  # Sync every 15s by default
        engine: Any = None,
        batch_size: int = 100,
    ):
        self.interval_seconds = interval_seconds
        self._last_run: float = 0.0
        self._engine = engine
        self._batch_size = batch_size
        self._turso: TursoBackend | None = None

        if config.TURSO_DATABASE_URL and config.TURSO_AUTH_TOKEN:
            self._turso = TursoBackend(url=config.TURSO_DATABASE_URL, auth_token=config.TURSO_AUTH_TOKEN)

    def _ensure_remote_table(self):
        """Ensure the 'transactions' table exists on the edge."""
        # Simple schema matching the local transactions
        schema = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            project TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """
        # Note: this would ideally be async, but called from sync daemon context
        # We'll rely on the underlying async loop mapping or just use threaded execution.
        import asyncio

        asyncio.run(self._turso.connect())
        asyncio.run(self._turso.execute(schema))

    def _get_last_synced_id(self) -> int:
        import asyncio

        try:
            res = asyncio.run(self._turso.execute("SELECT MAX(id) as max_id FROM transactions"))
            if res and res[0].get("max_id") is not None:
                return res[0]["max_id"]
        except Exception as e:
            logger.warning("CloudSync: Failed to get remote sync state: %s", e)
        return 0

    def check(self) -> list[CloudSyncAlert]:
        """Run Edge Sync if interval has elapsed."""
        if not self._engine or not self._turso:
            return []

        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        alerts: list[CloudSyncAlert] = []
        try:
            last_id = self._get_last_synced_id()
            conn = self._engine._get_sync_conn()

            cursor = conn.execute(
                "SELECT id, project, action, detail, prev_hash, hash, timestamp "
                "FROM transactions WHERE id > ? ORDER BY id ASC LIMIT ?",
                (last_id, self._batch_size),
            )
            rows = cursor.fetchall()

            if rows:
                params_list = []
                for row in rows:
                    params_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6]))

                import asyncio

                asyncio.run(
                    self._turso.executemany(
                        "INSERT INTO transactions "
                        "(id, project, action, detail, prev_hash, hash, timestamp) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        params_list,
                    )
                )

                alerts.append(
                    CloudSyncAlert(
                        synced_count=len(rows),
                        last_id=params_list[-1][0],
                        message=f"Synced {len(rows)} transactions to Turso Edge Cloud.",
                        latency_ms=(time.monotonic() - now) * 1000,
                    )
                )

            self._last_run = now

        except (ValueError, OSError, RuntimeError, ImportError, sqlite3.Error) as e:
            logger.error("Autonomous Cloud Sync failed: %s", e)

        return alerts
