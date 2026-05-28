"""Autonomous Tombstone Monitor (El Barrendero)."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

from cortex.extensions.daemon.models import TombstoneAlert

logger = logging.getLogger("moskv-daemon")


class TombstoneMonitor:
    """Physically deletes logically tombstoned facts during the late-night maintenance window.

    Protects daytime IOPs by restricting heavy DELETE and VACUUM/OPTIMIZE operations
    to the 03:00 - 05:00 UTC window.
    """

    def __init__(
        self,
        db_path: Path | str,
        interval_seconds: int = 3600,  # check every hour
        start_hour: int = 3,  # 03:00 UTC
        end_hour: int = 5,  # 05:00 UTC
    ):
        self.db_path = Path(db_path)
        self.interval_seconds = interval_seconds
        self.start_hour = start_hour
        self.end_hour = end_hour
        self._last_run: float = 0

    def _in_maintenance_window(self) -> bool:
        """Check if current UTC time is within the maintenance window."""
        now = datetime.fromtimestamp(time.time(), tz=UTC)
        return self.start_hour <= now.hour < self.end_hour

    def check(self) -> list[TombstoneAlert]:
        """Run physical sweep if in maintenance window and interval elapsed."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        if not self._in_maintenance_window():
            return []

        if not self.db_path.exists():
            return []

        self._last_run = now

        try:
            from cortex.compaction.gc import GarbageCollector
            from cortex.engine import CortexEngine
            from cortex.events.loop import sovereign_run

            initial_size = self.db_path.stat().st_size

            async def _run_guarded_gc() -> dict:
                engine = CortexEngine(self.db_path)
                try:
                    gc = GarbageCollector(engine)
                    return await gc.run_gc(batch_size=1000, force=True)
                finally:
                    await engine.close()

            stats = sovereign_run(_run_guarded_gc())
            total_deleted = int(stats.get("deleted_facts", 0))
            if total_deleted == 0:
                return []

            logger.info("TombstoneMonitor: Evicted %d logically deleted facts.", total_deleted)

            if total_deleted > 5000:
                from cortex.database.core import connect as db_connect

                with db_connect(self.db_path, timeout=5, isolation_level=None) as conn:  # type: ignore[type-error]
                    conn.execute("PRAGMA optimize")

            try:
                final_size = self.db_path.stat().st_size
            except OSError:
                final_size = initial_size
            freed_mb = (initial_size - final_size) / (1024 * 1024)

            return [
                TombstoneAlert(
                    deleted_facts=total_deleted,
                    freed_mb=freed_mb,
                    message=(f"Barrido Nocturno completado: {total_deleted} facts purgados."),
                )
            ]

        except (ValueError, OSError, RuntimeError, sqlite3.Error) as e:
            logger.error("Tombstone Sweep failed: %s", e)
            return []
