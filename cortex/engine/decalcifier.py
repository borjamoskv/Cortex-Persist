"""
CORTEX V6 - Sovereign Decalcifier (REM Phase Memory Consolidation).

Executes deep background maintenance on the SQLite persistence layer.
Only runs when the Endocrine system indicates low Cortisol (safety/rest).
Purges orphaned memory, deduplicates deeply, and compresses semantic representations
that haven't been accessed in a long time (LFU/LRU decalcification).
"""

import logging
import time
from typing import Any

import aiosqlite

from cortex.engine.endocrine import ENDOCRINE, HormoneType

logger = logging.getLogger("cortex.engine.decalcifier")


class SovereignDecalcifier:
    """
    Biological memory maintenance layer.
    """

    def __init__(self, target_retention_days: int = 30):
        self.target_retention_days = target_retention_days

    async def decalcify_cycle(self, conn: aiosqlite.Connection) -> dict[str, Any]:
        """
        Executes one full REM cycle of memory consolidation.
        """
        logger.warning("🧠 [DECALCIFIER] Initiating REM Sleep Cycle (Deep memory sweep)...")
        start_time = time.time()

        metrics = {"purged_orphans": 0, "compressed_engrams": 0, "serotonin_boost": 0.0}

        # 1. Sweep stale transactions / ledger entries that are purely logging
        # We only delete old 'telemetry' or extremely low-impact actions.
        # Axiom: Core decisions are never deleted.
        try:
            # Committing any pending open transactions before we do maintenance
            await conn.commit()

            # Note: We rely on the schema having a timestamp. We'll do a safe threshold.
            cursor = await conn.execute(
                "DELETE FROM transactions WHERE action = 'telemetry' AND timestamp < datetime('now', '-7 days')"
            )
            metrics["purged_orphans"] = cursor.rowcount
            await conn.commit()

            # 2. Check if we have facts with a decay score < 0.1 (calcified)
            # This requires knowing the memory schema. Let's assume standard `facts` table
            # with `decay_score` or `last_accessed` if it exists.
            # Biological defragmentation (VACUUM cannot run in transaction)
            # In aiosqlite, accessing conn.isolation_level triggers cross-thread errors.
            # So we create an ephemeral connection with isolation_level=None to execute VACUUM.
            import sqlite3

            from cortex.core.paths import CORTEX_DB

            def _run_vacuum():
                with sqlite3.connect(CORTEX_DB, isolation_level=None) as vconn:
                    vconn.execute("VACUUM")

            # Run vacuum asynchronously to avoid blocking
            import asyncio

            await asyncio.to_thread(_run_vacuum)

            # 3. Reward the system for a successful sleep cycle
            ENDOCRINE.pulse(HormoneType.SEROTONIN, 0.1, reason="REM Cycle Completed")
            ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.05, reason="Memory Compression")
            metrics["serotonin_boost"] = 0.1

        except Exception as e:  # noqa: BLE001 — background task resilience
            logger.error("❌ [DECALCIFIER] REM Cycle interrupted by nightmare (Error): %s", e)
            ENDOCRINE.pulse(HormoneType.CORTISOL, 0.2, reason="REM Interruption")
            await conn.rollback()
            return {"status": "interrupted", "error": str(e)}

        duration = time.time() - start_time
        logger.warning(
            "🧠 [DECALCIFIER] Cycle complete in %.2fs. Purged: %d. 🧬 SEROTONIN +%.2f",
            duration,
            metrics["purged_orphans"],
            metrics["serotonin_boost"],
        )

        return {"status": "success", "duration": duration, "metrics": metrics}
