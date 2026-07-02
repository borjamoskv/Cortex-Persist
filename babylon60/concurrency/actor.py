# [C5-REAL] Exergy-Maximized
"""
cat_id: concurrency-actor
cat_type: module
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class BatchCommitActor:
    """Actor-like message processing queue for batching SQLite writes.
    Prevents SQLite WAL connection blockages and lock contention under high-frequency writes.
    """

    def __init__(
        self, commit_callback: Callable[[list[dict[str, Any]]], None], flush_interval_ms: int = 1000
    ):
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.commit_callback = commit_callback
        self.flush_interval = flush_interval_ms / 1000.0
        self.is_running = False
        self._loop_task: asyncio.Task | None = None

    def start(self) -> None:
        if not self.is_running:
            self.is_running = True
            self._loop_task = asyncio.create_task(self._process_queue())
            logger.info("BatchCommitActor processing loops activated.")

    async def send_write(self, transaction: dict[str, Any]) -> None:
        """Pushes a transaction task into the in-memory queue."""
        await self.queue.put(transaction)

    async def _process_queue(self) -> None:
        while self.is_running:
            await asyncio.sleep(self.flush_interval)

            batch = []
            while not self.queue.empty():
                batch.append(await self.queue.get())
                self.queue.task_done()

            if batch:
                try:
                    logger.debug("Flushing batch commit of size=%d", len(batch))
                    self.commit_callback(batch)
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to commit batch to SQLite database: %s", e)

    async def stop(self) -> None:
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            logger.info("BatchCommitActor processing loops deactivated.")
