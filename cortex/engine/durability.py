"""
DURABILITY-1 — CORTEX Persistence Supervisor (Ω₃ / Ω₅).
Implements the two-layer persistence strategy:
1. C5 Supervisor: Interval-based background flushing.
2. C4 atexit: Fallback for clean process termination.
"""

import asyncio
import atexit
import logging
from typing import Any

logger = logging.getLogger("cortex.durability")


class PersistenceSupervisor:
    """The Sovereign Guardian of Continuity."""

    def __init__(self, engine: Any, interval: float = 60.0):
        self._engine = engine
        self._interval = interval
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._queue: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

        # Register C4 fallback
        atexit.register(self._atexit_fallback)

    async def start(self):
        """Ignites the C5 Supervisor layer."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._loop())
            logger.info("PersistenceSupervisor: C5 layer ignited (Interval: %.1fs)", self._interval)

    async def stop(self):
        """Hibernates the supervisor and forces a final flush."""
        if self._task:
            self._stop_event.set()
            await self._task
            await self.flush()
            logger.info("PersistenceSupervisor: C5 layer hibernated.")

    async def enqueue(self, fact_data: dict[str, Any]):
        """Non-blocking queueing of facts for persistent storage."""
        async with self._lock:
            self._queue.append(fact_data)
            # 150/100: Pressure trigger
            if len(self._queue) > 50:
                asyncio.create_task(self.flush(reason="queue_pressure"))

    async def flush(self, reason: str = "interval"):
        """Commits all enqueued facts to the CORTEX ledger."""
        async with self._lock:
            if not self._queue:
                return

            to_store = self._queue.copy()
            self._queue.clear()

            logger.debug(
                "PersistenceSupervisor: Flushing %d facts (Reason: %s)", len(to_store), reason
            )
            try:
                # Store them using the sync connection to ensure durability if loop fails
                sync_conn = self._engine._get_sync_conn()
                with sync_conn:
                    for fact in to_store:
                        # Direct injection bypassing mixins for speed
                        await self._engine.store(
                            conn=None,  # Will use its own session
                            **fact,
                        )
                logger.info("PersistenceSupervisor: Flush complete.")
            except (OSError, RuntimeError) as e:
                logger.error("PersistenceSupervisor: Flush failed: %s", e)
                # Re-queue on failure? Optional.
                self._queue.extend(to_store)

    async def _loop(self):
        """The heartbeat of the persistence layer."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
                break  # Event was set, exit loop
            except asyncio.TimeoutError:
                await self.flush(reason="heartbeat")
            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError) as e:
                logger.error("PersistenceSupervisor: Heartbeat loop error: %s", e)

    def _atexit_fallback(self):
        """C4 Fallback: Emergency flush on process exit."""
        if not self._queue:
            return

        print(f"⚠️ [CORTEX] Emergency flush: {len(self._queue)} facts pending...")
        try:
            # Synchronous emergency store
            sync_conn = self._engine._get_sync_conn()
            with sync_conn:
                for fact in self._queue:
                    # We use store_sync or manual SQL
                    self._engine.store_sync(**fact)
            print("✅ [CORTEX] Emergency flush successful.")
        except (OSError, RuntimeError) as e:
            print(f"❌ [CORTEX] Emergency flush failed: {e}")
