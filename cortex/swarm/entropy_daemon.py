# [C5-REAL] Exergy-Maximized
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class EntropyDaemon:
    """
    [C5-REAL] Thermodynamic Hygiene Daemon.
    Separates Survival (ExergyDaemon) from Maintenance (EntropyDaemon).
    Its function is to reclaim physical disk space (Vacuum, WAL truncation, Fragmentation).
    Operates on a secondary asynchronous thread and executes VACUUM with minimal I/O interruption.
    """

    def __init__(self, db_path: str, scan_interval: int = 600):
        self.db_path = db_path
        self.interval = scan_interval
        self._running = False
        self._task = None

    async def _daemon_loop(self):
        logger.info("[EntropyDaemon] Active. SQLite garbage collection initiated.")
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                await self._hygiene_sweep()
            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error(f"[EntropyDaemon] Failure during hygiene: {e}")

    async def _hygiene_sweep(self):
        """Reclaims physical space returning it to the OS."""
        logger.info("[EntropyDaemon] Executing VACUUM and WAL hygiene...")
        db_size_before = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        from cortex.database.core import connect_async

        async with await connect_async(self.db_path, timeout=60) as conn:
            # Checkpoint the Write-Ahead Log (WAL) to database file and truncate WAL
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            # Reclaim empty pages back to OS
            await conn.execute("VACUUM;")

        db_size_after = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        recovered = (db_size_before - db_size_after) / 1024

        if recovered > 0:
            logger.info(f"[EntropyDaemon] Cleanup successful. Recovered space: {recovered:.2f} KB")

        # APEX-008: Ouroboros Immune - scan for recursive logging
        try:
            from cortex.engine.causal.ouroboros_immune import OuroborosImmuneSystem

            immune = OuroborosImmuneSystem()
            quarantined = immune.scan_and_quarantine()
            if quarantined:
                logger.warning(
                    f"[EntropyDaemon] ISOLATED: {len(quarantined)} files by Ouroboros."
                )
        except Exception as e:
            logger.warning(f"[EntropyDaemon] Ouroboros Immune failure: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                logger.warning("Suppressed exception: %s", exc)
            logger.info("[EntropyDaemon] Terminated.")
