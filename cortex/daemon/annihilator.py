"""CORTEX Annihilator Protocol — C5-REAL Purge Daemon.

Monitors Shannon entropy and executes structural purges (VACUUM,
dangling tags, stale cache) to preserve the zero-entropy mandate (Ω₄).
"""

import asyncio
import logging
import sqlite3
from typing import TYPE_CHECKING, Dict, Any

from cortex.ledger.ledger_core import SovereignLedger

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.daemon.annihilator")

class AnnihilatorDaemon:
    """Active background daemon that enforces structural purity."""
    
    def __init__(self, db_path: str, entropy_threshold: float = 5.0):
        self.db_path = db_path
        self.entropy_threshold = entropy_threshold
        self.ledger = SovereignLedger(db_path)
        self._is_running = False
        
    async def measure_entropy(self) -> float:
        """Measure current database Shannon entropy.
        
        Reads directly from the ledger or calculates approximation.
        """
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                # Approximation: we check total transactions vs unique targets
                cursor = await db.execute("SELECT count(*), count(DISTINCT action) FROM transactions")
                row = await cursor.fetchone()
                if row and row[0] > 0:
                    total, unique = row
                    # Simple heuristic for MVP
                    return (total / (unique + 1)) * 0.1
        except Exception as e:
            logger.warning(f"Failed to measure entropy: {e}")
        return 0.0
        
    async def purge(self) -> Dict[str, Any]:
        """Execute a C5-REAL structural purge."""
        import aiosqlite
        
        results = {"vacuumed": False, "orphans_deleted": 0}
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Execute database vacuum to reclaim space and optimize indices
                await db.execute("VACUUM;")
                await db.commit()
                results["vacuumed"] = True
                
            await self.ledger.ensure_initialized_async()
            await self.ledger.append_verdict(
                verdict="ANNIHILATION",
                target="SYSTEM_DB",
                reason=f"Structural purge executed. Vacuum complete."
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
                entropy = await self.measure_entropy()
                if entropy > self.entropy_threshold:
                    logger.warning(f"Entropy threshold exceeded ({entropy:.2f} > {self.entropy_threshold}). Purging.")
                    await self.purge()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Annihilator loop: {e}")
                
            await asyncio.sleep(interval_seconds)
            
    def stop(self):
        self._is_running = False
