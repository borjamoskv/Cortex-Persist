"""
CORTEX v5.0 — Vector Memory Garbage Collection Pipeline.

Implements deferred physical deletion for tombstoned facts.
To safeguard database IOPS during peak daytime traffic, physical deletion
is deferred to off-peak hours (e.g., early morning).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.gc")


class GarbageCollector:
    """Garbage collector for physically deleting tombstoned facts off-peak."""

    def __init__(self, engine: AsyncCortexEngine):
        self.engine = engine

    def _is_off_peak(self) -> bool:
        """Determines if current time is within off-peak hours (02:00 - 05:00)."""
        now = datetime.now(timezone.utc)
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

        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT id FROM facts WHERE is_tombstoned = 1 LIMIT ?", (batch_size,)
            )
            rows = await cursor.fetchall()

            if not rows:
                logger.info("Garbage Collector: No tombstoned facts found.")
                return stats

            fact_ids = [row[0] for row in rows]

            try:
                await self._execute_physical_deletion(conn, fact_ids)
                stats["deleted_embeddings"] += len(fact_ids)
                stats["deleted_facts"] += len(fact_ids)
                await conn.commit()

            except (sqlite3.Error, OSError) as e:
                logger.error("Failed to execute GC batch: %s", e)
                stats["errors"].append(str(e))
                await conn.rollback()
                stats["status"] = "failed"

        logger.info(
            "Garbage Collector Run Complete: %d facts and %d vectors physically removed.",
            stats["deleted_facts"],
            stats["deleted_embeddings"],
        )
        return stats

    async def _execute_physical_deletion(self, conn: Any, fact_ids: list[Any]) -> None:
        """Execute physical deletion sequences for a batch of fact IDs."""
        # 1. Physical vector deletion
        # In sqlite-vec vec0 tables, WHERE IN () is often not fully supported, so we iterate
        for fact_id in fact_ids:
            await conn.execute("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,))
            await conn.execute("DELETE FROM specular_embeddings WHERE fact_id = ?", (fact_id,))

        # 2. Pruned embeddings archive deletion
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pruned_embeddings'"
        )
        if await cursor.fetchone():
            await conn.executemany(
                "DELETE FROM pruned_embeddings WHERE fact_id = ?",
                [(fid,) for fid in fact_ids],
            )

        # 3. Consensus structure structural deletion
        placeholders = ",".join(["?"] * len(fact_ids))
        await conn.execute(
            f"DELETE FROM consensus_votes_v2 WHERE fact_id IN ({placeholders})", fact_ids
        )
        await conn.execute(
            f"DELETE FROM consensus_votes WHERE fact_id IN ({placeholders})", fact_ids
        )
        await conn.execute(
            f"DELETE FROM consensus_outcomes WHERE fact_id IN ({placeholders})", fact_ids
        )

        # 4. Final physical deletion of the fact itself
        await conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)
