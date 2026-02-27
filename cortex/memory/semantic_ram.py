"""
CORTEX v6 — Semantic RAM (Dynamic RAG) & Hebbian Daemon.

Zero-Copy Infinite Minds architecture pillar.
Implements Read-as-Rewrite: as vectors are co-activated and proved useful,
a background Hebbian Daemon updates their topology (success_rate / embedding shift)
without blocking the main event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

__all__ = ["DynamicSemanticSpace", "HebbianDaemon"]

logger = logging.getLogger("cortex.memory.semantic_ram")


class HebbianDaemon:
    """Non-blocking daemon that applies Hebbian learning (Read-as-Rewrite).
    
    When facts are successfully utilized in a context, they emit a semantic pulse.
    This daemon receives the pulses and asynchronously mutates the success_rate
    or the topological position of the vectors in the database, 
    creating Semantic Gravity without I/O latency on the main thread.
    """

    __slots__ = ("_store", "_queue", "_worker_task")

    def __init__(self, store: SovereignVectorStoreL2) -> None:
        self._store = store
        self._queue: asyncio.Queue[tuple[str, float]] = asyncio.Queue(maxsize=10000)
        self._worker_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the background daemon. Should be called during Engine boot."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._pulse_loop())
            logger.info("HebbianDaemon: Semantic gravitational field stabilized (Started).")

    async def stop(self) -> None:
        """Gracefully stop the daemon."""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("HebbianDaemon: Semantic gravitational field collapsed (Stopped).")

    def emit_pulse(self, fact_id: str, resonance_delta: float = 0.05) -> None:
        """Emit a semantic pulse for a fact. 
        
        This is an O(1) non-blocking enqueue. The daemon will process it.
        """
        try:
            self._queue.put_nowait((fact_id, resonance_delta))
        except asyncio.QueueFull:
            logger.warning("HebbianDaemon: Event horizon full. Dropping pulse for %s", fact_id)

    async def _pulse_loop(self) -> None:
        """The gravitational engine. Processes pulses and mutates topology."""
        while True:
            try:
                # Process in batches to minimize DB lock contention
                batch: dict[str, float] = {}
                
                # Wait for at least one pulse
                fact_id, delta = await self._queue.get()
                batch[fact_id] = batch.get(fact_id, 0.0) + delta
                self._queue.task_done()
                
                # Drain the queue up to 100 items per transaction
                while len(batch) < 100 and not self._queue.empty():
                    fid, d = self._queue.get_nowait()
                    batch[fid] = batch.get(fid, 0.0) + d
                    self._queue.task_done()
                
                await self._apply_mutations(batch)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("HebbianDaemon: Pulse mutation failed: %s", e)
                await asyncio.sleep(1.0)

    async def _apply_mutations(self, batch: dict[str, float]) -> None:
        """Applies topological shifts asynchronously using to_thread to avoid blocking."""
        if not batch:
            return

        def _mutate():
            conn = self._store._get_conn()
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                for fid, delta in batch.items():
                    # Read-as-Rewrite: Increment success_rate recursively
                    # Max success_rate capped at 5.0 to prevent runaway gravity
                    cursor.execute(
                        """
                        UPDATE facts_meta 
                        SET success_rate = MIN(5.0, success_rate + ?) 
                        WHERE id = ?
                        """, 
                        (delta, fid)
                    )
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

        # Execute DB writes in a threadpool to guarantee zero event loop blocking
        async with self._store._lock:
            await asyncio.to_thread(_mutate)


class DynamicSemanticSpace:
    """Wraps the SovereignVectorStoreL2 to provide Read-as-Rewrite capabilities."""

    __slots__ = ("_store", "hebbian_daemon")

    def __init__(self, store: SovereignVectorStoreL2) -> None:
        self._store = store
        self.hebbian_daemon = HebbianDaemon(store)

    async def recall_and_pulse(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        pulse_delta: float = 0.01,
    ) -> list[Any]:
        """Recupera los vectores y automáticamente emite un pulso Hebbiano.
        
        Proof-of-concept del Read-as-Rewrite. En arquitecturas clásicas (RAG), 
        leer es gratis. Aquí, cada lectura que retorna un contexto útil refuerza 
        (rescribe) secretamente el tejido del espacio vectorial.
        """
        facts = await self._store.recall_secure(tenant_id, project_id, query, limit)
        
        # Emite pulso asíncrono para los top hits. 
        # Refuerza el conocimiento útil de manera autónoma.
        for fact in facts:
            self.hebbian_daemon.emit_pulse(fact.id, resonance_delta=pulse_delta)
            
        return facts
