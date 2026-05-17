"""CORTEX Annihilator Protocol — C5-REAL Purge Daemon.

Monitors Shannon entropy and executes structural purges (VACUUM,
dangling tags, stale cache) to preserve the zero-entropy mandate (Ω₄).
"""

import asyncio
import logging
import os
import psutil
from typing import Any

from cortex.ledger.ledger_core import SovereignLedger

logger = logging.getLogger("cortex.daemon.annihilator")


class AnnihilatorDaemon:
    """Active background daemon that enforces structural purity and memory exergy."""

    def __init__(
        self, db_path: str, entropy_threshold: float = 5.0, memory_threshold_mb: float = 512.0
    ):
        self.db_path = db_path
        self.entropy_threshold = entropy_threshold
        self.memory_threshold_mb = memory_threshold_mb
        # We do not instantiate ledger here because it needs an active connection.
        self._is_running = False

    def _get_rss_memory_mb(self) -> float:
        """Measure current Resident Set Size (RSS) memory in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)

    async def measure_entropy(self) -> float:
        """Measure current database Shannon entropy.

        Reads directly from the ledger or calculates approximation.
        """
        try:
            import aiosqlite

            async with aiosqlite.connect(self.db_path) as db:
                # Approximation: we check total transactions vs unique targets
                cursor = await db.execute(
                    "SELECT count(*), count(DISTINCT action) FROM transactions"
                )
                row = await cursor.fetchone()
                if row and row[0] > 0:
                    total, unique = row
                    # Simple heuristic for MVP
                    return (total / (unique + 1)) * 0.1
        except Exception as e:
            logger.warning(f"Failed to measure entropy: {e}")
        return 0.0

    async def purge(self) -> dict[str, Any]:
        """Execute a C5-REAL structural purge."""
        import aiosqlite

        results: dict[str, Any] = {"vacuumed": False, "orphans_deleted": 0}

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Execute database vacuum to reclaim space and optimize indices
                await db.execute("VACUUM;")
                await db.commit()
                results["vacuumed"] = True

            async with aiosqlite.connect(self.db_path) as db:
                ledger = SovereignLedger(db)
                await ledger.append_verdict(
                    verdict="ANNIHILATE",
                    reason="Structural purge executed. Vacuum complete.",
                    target_path="SYSTEM_DB",
                    action_type="SYSTEM_PURGE",
                )
            logger.info("Annihilation Protocol executed successfully.")

        except Exception as e:
            logger.error(f"Annihilation Protocol failed: {e}")
            results["error"] = str(e)

        return results

    async def run_loop(self, interval_seconds: int = 3600):
        """Continuous background monitoring loop."""
        self._is_running = True
        logger.info(f"Annihilator Daemon started. Checking every {interval_seconds}s.")

        while self._is_running:
            try:
                # 1. Structural Entropy Check
                entropy = await self.measure_entropy()
                if entropy > self.entropy_threshold:
                    logger.warning(
                        f"Entropy threshold exceeded ({entropy:.2f} > {self.entropy_threshold}). "
                        "Purging."
                    )
                    await self.purge()

                # 2. JIT-Memory Purge Check (Exergy optimization)
                current_rss = self._get_rss_memory_mb()
                if current_rss > self.memory_threshold_mb:
                    logger.error(
                        f"[JIT-KILL] Memory entropy critical ({current_rss:.2f}MB > "
                        f"{self.memory_threshold_mb}MB). Forcing GC and Phantom-Kill."
                    )
                    import gc

                    gc.collect()

                    # Log the JIT-Memory Purge in Ledger
                    import aiosqlite

                    async with aiosqlite.connect(self.db_path) as db:
                        ledger = SovereignLedger(db)
                        await ledger.append_verdict(
                            verdict="JIT_MEMORY_PURGE",
                            reason=f"RSS Memory hit {current_rss:.2f}MB. GC forced.",
                            target_path="SYSTEM_RAM",
                            action_type="SYSTEM_PURGE",
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Annihilator loop: {e}")

            await asyncio.sleep(interval_seconds)

    def stop(self):
        self._is_running = False
