# [C5-REAL] Exergy-Maximized
"""
Vector Memory Garbage Collection Pipeline.

Implements deferred physical deletion for tombstoned facts.
To safeguard database IOPS during peak daytime traffic, physical deletion
is deferred to off-peak hours (e.g., early morning).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timezone
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
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc)
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
        # Check which tables exist in sqlite_master to avoid no such table errors
        target_tables = {
            "fact_embeddings",
            "pruned_embeddings",
            "consensus_votes_v2",
            "consensus_votes",
            "consensus_outcomes",
            "causal_edges",
            "enrichment_jobs",
            "entity_relations",
            "fact_tags",
        }
        placeholders_in = ",".join(["?"] * len(target_tables))
        cursor = await conn.execute(
            f"SELECT name FROM sqlite_master WHERE name IN ({placeholders_in})",
            list(target_tables),
        )
        rows = await cursor.fetchall()
        existing_tables = {row[0] for row in rows}

        # 1. Physical vector deletion (Ouroboros optimization: executemany)
        # We rely on executemany to push the loop down to C-level API
        if "fact_embeddings" in existing_tables:
            await conn.executemany(
                "DELETE FROM fact_embeddings WHERE fact_id = ?", [(fid,) for fid in fact_ids]
            )

        # 2. Pruned embeddings archive deletion
        if "pruned_embeddings" in existing_tables:
            await conn.executemany(
                "DELETE FROM pruned_embeddings WHERE fact_id = ?",
                [(fid,) for fid in fact_ids],
            )

        # 3. Consensus structure and referencing tables structural deletion
        placeholders = ",".join(["?"] * len(fact_ids))

        if "consensus_votes_v2" in existing_tables:
            await conn.execute(
                f"DELETE FROM consensus_votes_v2 WHERE fact_id IN ({placeholders})", fact_ids
            )
        if "consensus_votes" in existing_tables:
            await conn.execute(
                f"DELETE FROM consensus_votes WHERE fact_id IN ({placeholders})", fact_ids
            )
        if "consensus_outcomes" in existing_tables:
            await conn.execute(
                f"DELETE FROM consensus_outcomes WHERE fact_id IN ({placeholders})", fact_ids
            )
        if "causal_edges" in existing_tables:
            await conn.execute(
                f"DELETE FROM causal_edges WHERE fact_id IN ({placeholders})", fact_ids
            )
        if "enrichment_jobs" in existing_tables:
            await conn.execute(
                f"DELETE FROM enrichment_jobs WHERE fact_id IN ({placeholders})", fact_ids
            )
        if "entity_relations" in existing_tables:
            await conn.execute(
                f"DELETE FROM entity_relations WHERE source_fact_id IN ({placeholders})", fact_ids
            )
        if "fact_tags" in existing_tables:
            await conn.execute(f"DELETE FROM fact_tags WHERE fact_id IN ({placeholders})", fact_ids)

        # 4. Final physical deletion of the fact itself
        await conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)
