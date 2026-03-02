"""Autonomous Tombstone Monitor (El Barrendero)."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from cortex.daemon.models import TombstoneAlert

logger = logging.getLogger("moskv-daemon")


class TombstoneMonitor:
    """Physically deletes logically tombstoned facts during the late-night maintenance window.

    Protects daytime IOPs by restricting heavy DELETE and VACUUM/OPTIMIZE operations
    to the 03:00 - 05:00 local time window.
    """

    def __init__(
        self,
        db_path: Path | str,
        interval_seconds: int = 3600,  # check every hour
        start_hour: int = 3,  # 03:00 AM
        end_hour: int = 5,  # 05:00 AM
    ):
        self.db_path = Path(db_path)
        self.interval_seconds = interval_seconds
        self.start_hour = start_hour
        self.end_hour = end_hour
        self._last_run: float = 0

    def _in_maintenance_window(self) -> bool:
        """Check if current local time is within the maintenance window."""
        now = datetime.now()  # Local time
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
            # Using basic sqlite3 to bypass connection pools / WAL constraints if needed
            with sqlite3.connect(
                self.db_path,
                timeout=30,
                isolation_level="IMMEDIATE",  # Exclusive write transaction
            ) as conn:
                cursor = conn.cursor()

                # Get count of facts to sweep
                cursor.execute("SELECT COUNT(*) FROM facts WHERE is_tombstoned = 1")
                to_delete = cursor.fetchone()[0]

                if to_delete == 0:
                    return []

                logger.info("TombstoneMonitor: Evicting %d logically deleted facts.", to_delete)

                initial_size = self.db_path.stat().st_size

                # 1. Main Delete (Cascade handling handles vector indexes depending on schema triggers)
                # But to be safe, we explicitly clear related vectors if cascade is off.
                cursor.execute("SELECT id FROM facts WHERE is_tombstoned = 1")
                fact_ids = [r[0] for r in cursor.fetchall()]

                # We batch deletes to avoid mammoth transactions
                batch_size = 1000
                total_deleted = 0
                for i in range(0, len(fact_ids), batch_size):
                    batch = fact_ids[i : i + batch_size]
                    id_list = ",".join("?" * len(batch))

                    try:
                        cursor.execute(
                            f"DELETE FROM fact_embeddings WHERE fact_id IN ({id_list})", batch
                        )
                        cursor.execute(f"DELETE FROM facts_fts WHERE rowid IN ({id_list})", batch)
                        cursor.execute(f"DELETE FROM facts WHERE id IN ({id_list})", batch)
                        conn.commit()
                        total_deleted += len(batch)
                    except sqlite3.Error as batch_err:
                        logger.warning(
                            "Batch sweep issue (might be ignored if tables missing): %s", batch_err
                        )

                # Optimizing standard FTS / standard fragmentation if heavy sweeping occurred
                if total_deleted > 5000:
                    conn.execute("PRAGMA optimize")

                final_size = self.db_path.stat().st_size
                freed_mb = (initial_size - final_size) / (1024 * 1024)

                return [
                    TombstoneAlert(
                        deleted_facts=total_deleted,
                        freed_mb=freed_mb,
                        message=f"Barrido Nocturno completado: {total_deleted} facts purgados permanentemente.",
                    )
                ]

        except (ValueError, OSError, RuntimeError, sqlite3.Error) as e:
            logger.error("Tombstone Sweep failed: %s", e)
            return []
