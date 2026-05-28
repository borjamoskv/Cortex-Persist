"""
CORTEX v5.0 — Vector Memory Garbage Collection Pipeline.

Implements deferred physical deletion for tombstoned facts.
To safeguard database IOPS during peak daytime traffic, physical deletion
is deferred to off-peak hours (e.g., early morning).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("cortex.gc")


class GarbageCollector:
    """Garbage collector for physically deleting tombstoned facts off-peak."""

    def __init__(self, engine: AsyncCortexEngine):
        self.engine = engine

    def _is_off_peak(self) -> bool:
        """Determines if current time is within off-peak hours (02:00 - 05:00)."""
        now = datetime.fromtimestamp(time.time(), tz=UTC)
        return 2 <= now.hour < 5

    async def run_gc(self, batch_size: int = 500, force: bool = False) -> dict[str, Any]:
        """
        Execute GC physically deleting facts marked as tombstoned.
        Should be scheduled by a daemon during off-peak hours (e.g., 02:00 - 05:00).
        """
        if not self._is_off_peak() and not force:
            logger.info("Garbage Collector: Skipping execution (peak hours detected).")
            return {
                "status": "skipped",
                "reason": "peak_hours",
                "deleted_facts": 0,
                "deleted_embeddings": 0,
                "errors": [],
            }

        stats: dict[str, Any] = {
            "status": "completed",
            "deleted_facts": 0,
            "deleted_embeddings": 0,
            "errors": [],
        }

        try:
            async with self.engine.session() as conn:
                cursor = await conn.execute(
                    "SELECT id, COALESCE(tenant_id, 'default') "
                    "FROM facts WHERE is_tombstoned = 1 LIMIT ?",
                    (batch_size,),
                )
                rows = await cursor.fetchall()

        except (sqlite3.Error, OSError) as e:
            logger.error("Failed to select GC batch: %s", e)
            stats["errors"].append(str(e))
            stats["status"] = "failed"
            return stats

        if not rows:
            logger.info("Garbage Collector: No tombstoned facts found.")
            return stats

        for fact_id, tenant_id in rows:
            try:
                purged = await self.engine.purge(
                    int(fact_id),
                    tenant_id=str(tenant_id or "default"),
                    force=True,
                )
            except (sqlite3.Error, OSError, RuntimeError, TypeError, ValueError) as e:
                logger.error("Failed to purge tombstoned fact %s: %s", fact_id, e)
                stats["errors"].append(str(e))
                stats["status"] = "failed"
                continue

            if purged:
                stats["deleted_embeddings"] += 1
                stats["deleted_facts"] += 1

        logger.info(
            "Garbage Collector Run Complete: %d facts and %d vectors physically removed.",
            stats["deleted_facts"],
            stats["deleted_embeddings"],
        )
        return stats
