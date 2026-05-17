"""cortex/memory/auto_management.py - Ledger Auto Management Daemon.

Prevents CONTEXT_LEDGER from overflowing its storage bounds (e.g., 1.2GB)
by automatically archiving older events to cortex_archive.db and running
WAL checkpoints to reclaim physical disk exergy.
"""

import asyncio
import logging
import os

from cortex.memory.ledger import EventLedgerL3

logger = logging.getLogger("cortex.memory.auto_management")


class LedgerAutoManagementDaemon:
    """Background daemon to proactively manage EventLedgerL3 size."""

    def __init__(
        self,
        ledger: EventLedgerL3,
        tenant_id: str,
        max_db_size_mb: float = 1000.0,
        retain_limit: int = 1000,
        archive_path: str = "cortex_archive.db",
        check_interval_seconds: int = 60,
        db_path: str | None = None,
    ):
        self.ledger = ledger
        self.tenant_id = tenant_id
        self.max_db_size_mb = max_db_size_mb
        self.retain_limit = retain_limit
        self.archive_path = archive_path
        self.check_interval_seconds = check_interval_seconds
        self.db_path = db_path
        self._task: asyncio.Task | None = None
        self._running = False

    def get_db_size_mb(self) -> float:
        """Calculate the total size of the database and its WAL file in MB."""
        db_path = self.db_path
        if not db_path:
            # Fallback
            db_path = "cortex.db"
            if hasattr(self.ledger._conn, "_path"):
                db_path = self.ledger._conn._path  # type: ignore
            elif hasattr(self.ledger._conn, "database"):
                db_path = self.ledger._conn.database  # type: ignore

        total_size = 0.0
        try:
            if os.path.exists(db_path):
                total_size += os.path.getsize(db_path)
            wal_path = f"{db_path}-wal"
            if os.path.exists(wal_path):
                total_size += os.path.getsize(wal_path)
        except OSError as e:
            logger.warning(f"Failed to check db size: {e}")

        return total_size / (1024 * 1024)

    async def _daemon_loop(self):
        """Infinite loop to periodically check and compact the ledger."""
        logger.info(
            f"[AUTO-MANAGEMENT] Daemon started. Monitoring {self.tenant_id} ledger. "
            f"Max size: {self.max_db_size_mb}MB"
        )
        while self._running:
            try:
                current_size = self.get_db_size_mb()
                if current_size > self.max_db_size_mb:
                    logger.warning(
                        f"[OVERFLOW_PREVENTION] Ledger size {current_size:.2f}MB exceeds "
                        f"{self.max_db_size_mb}MB limit. Initiating compaction..."
                    )
                    archived = await self.ledger.compact_ledger(
                        tenant_id=self.tenant_id,
                        retain_limit=self.retain_limit,
                        archive_path=self.archive_path,
                    )
                    logger.info(
                        f"[AUTO-MANAGEMENT] Compaction complete. Archived {archived} events. "
                        f"New size: {self.get_db_size_mb():.2f}MB"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AUTO-MANAGEMENT] Compaction check failed: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    def start(self):
        """Starts the daemon loop in the background."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    def stop(self):
        """Stops the daemon."""
        self._running = False
        if self._task:
            self._task.cancel()
