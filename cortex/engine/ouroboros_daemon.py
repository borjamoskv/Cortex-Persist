import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class OuroborosDaemon:
    """
    Ouroboros Daemon (Apoptosis)
    Watchdog for Weaponized Forgetting. Scans the active ledger/WAL and purges 
    facts/nodes that haven't been causally referenced in the topological graph
    for a specified Base-60 cycle period (e.g. 72 hours).
    """
    def __init__(self, check_interval_seconds: float = 3600.0, decay_threshold_ms: float = 259200000.0):
        # Default decay threshold: 72 hours in ms
        self.check_interval_seconds = check_interval_seconds
        self.decay_threshold_ms = decay_threshold_ms
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # Mock database of last access times: node_id -> timestamp_ms
        self._node_access_times: dict[str, float] = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._apoptosis_loop())
        logger.info("[Ouroboros] Daemon activated.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[Ouroboros] Daemon terminated.")

    def record_access(self, node_id: str, current_time_ms: float) -> None:
        """Record the causal access of a node."""
        self._node_access_times[node_id] = current_time_ms

    async def sweep_wal(self, current_time_ms: float) -> int:
        """
        Performs the semantic decay check.
        Returns the number of nodes purged.
        """
        purged_count = 0
        nodes_to_purge = []
        for node_id, last_access in self._node_access_times.items():
            if (current_time_ms - last_access) > self.decay_threshold_ms:
                nodes_to_purge.append(node_id)
                
        for node_id in nodes_to_purge:
            del self._node_access_times[node_id]
            purged_count += 1
            logger.debug("[Ouroboros] Purged node %s due to semantic decay.", node_id)
            
        return purged_count

    async def _apoptosis_loop(self) -> None:
        """The infinite background loop."""
        try:
            while self._running:
                # In a real implementation we would fetch current_time_ms from Babylon-60 engine
                import time
                current_time_ms = time.time() * 1000
                purged = await self.sweep_wal(current_time_ms)
                if purged > 0:
                    logger.info("[Ouroboros] Apoptosis sweep completed: %d nodes purged.", purged)
                    
                await asyncio.sleep(self.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[Ouroboros] Fatal error in apoptosis loop: %s", e)
