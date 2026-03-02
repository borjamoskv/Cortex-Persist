"""
CORTEX v5.0 — Vector Memory Garbage Collection Pipeline.

Implements deferred physical deletion for tombstoned facts.
To safeguard database IOPS during peak daytime traffic, physical deletion
is deferred to off-peak hours (e.g., early morning).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
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
        now = datetime.now()
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
                # 1. Borrado físico de vectores
                for fact_id in fact_ids:
                    # En vec0 no se suele poder hacer un WHERE id IN (), mejor un iterador
                    await conn.execute("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,))
                    await conn.execute(
                        "DELETE FROM specular_embeddings WHERE fact_id = ?", (fact_id,)
                    )
                    stats["deleted_embeddings"] += 1

                # 2. Borrado de pruned_embeddings si la tabla existe (pruner archive)
                cursor = await conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pruned_embeddings'"
                )
                if await cursor.fetchone():
                    for fact_id in fact_ids:
                        await conn.execute(
                            "DELETE FROM pruned_embeddings WHERE fact_id = ?", (fact_id,)
                        )

                # 3. Borrado estructural de consensus ligados al fact
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

                # 4. Por último, borrado físico del fact original
                await conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)
                stats["deleted_facts"] += len(fact_ids)

                await conn.commit()

            except (sqlite3.Error, OSError) as e:
                logger.error(f"Failed to execute GC batch: {e}")
                stats["errors"].append(str(e))
                await conn.rollback()
                stats["status"] = "failed"

        logger.info(
            "Garbage Collector Run Complete: %d facts and %d vectors physically removed.",
            stats["deleted_facts"],
            stats["deleted_embeddings"],
        )
        return stats
