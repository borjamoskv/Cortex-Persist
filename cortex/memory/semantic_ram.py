"""
CORTEX v7 — Semantic RAM & Topological Mutator (130/100 Sovereign Standard).

Zero-Copy Infinite Minds architecture pillar.
Implements Read-as-Rewrite: as vectors are co-activated and proved useful,
a background ThreadPool Mutator updates their topological position (effective vector)
using Numpy (GIL-released) towards the query vector.
This creates Semantic Gravity without I/O latency on the main thread.
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Final

import numpy as np

from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

__all__ = ["DynamicSemanticSpace", "SemanticMutator"]

logger = logging.getLogger("cortex.memory.semantic_ram")

# Sovereign 130/100 Constants
DECAY_LAMBDA: Final[float] = 0.00000802  # 24h half-life
EXCITATION_MAX: Final[float] = 100.0
LEARNING_RATE: Final[float] = 0.05


class SemanticMutator:
    """Non-blocking mutator that applies Topological Shifts (Read-as-Rewrite).

    When facts are successfully utilized in a context, they emit a semantic pulse.
    This daemon receives the pulses (along with the query vector) and asynchronously
    mutates the embeddings in the database via numpy vector math.
    """

    __slots__ = ("_store", "_queue", "_worker_task", "_pool")

    def __init__(self, store: SovereignVectorStoreL2) -> None:
        self._store = store
        self._queue: asyncio.Queue[tuple[list[float], str, float]] = asyncio.Queue(maxsize=10000)
        self._worker_task: asyncio.Task[None] | None = None
        # ThreadPoolExecutor to bypass Python GIL during Numpy topological operations
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ctx_mutator")

    def start(self) -> None:
        """Start the background daemon. Should be called during Engine boot."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._pulse_loop())
            logger.info("SemanticMutator: Topological gravitational field stabilized (Started).")

    async def stop(self) -> None:
        """Gracefully stop the daemon."""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._pool.shutdown(wait=False)
            logger.info("SemanticMutator: Topological gravitational field collapsed (Stopped).")

    def emit_pulse(
        self, query_vector: list[float], fact_id: str, excitation_delta: float = 20.0
    ) -> None:
        """Emit a topological pulse for a fact towards a query vector.

        This is an O(1) non-blocking enqueue. The daemon will process it.
        """
        try:
            self._queue.put_nowait((query_vector, fact_id, excitation_delta))
        except asyncio.QueueFull:
            logger.warning("SemanticMutator: Event horizon full. Dropping pulse for %s", fact_id)

    async def _pulse_loop(self) -> None:
        """The gravitational engine. Processes pulses and mutates topology."""
        while True:
            try:
                batch = await self._collect_batch()
                await self._apply_topological_shift(batch)
            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError, ValueError) as e:
                logger.error("SemanticMutator: Pulse mutation failed: %s", e)
                await asyncio.sleep(1.0)

    async def _collect_batch(self) -> dict[str, tuple[list[list[float]], float]]:
        """Collect and aggregate pulses into a batch before applying topological shifts."""
        batch: dict[str, tuple[list[list[float]], float]] = {}

        query_vec, fact_id, delta = await self._queue.get()
        batch[fact_id] = ([query_vec], delta)
        self._queue.task_done()

        while len(batch) < 100 and not self._queue.empty():
            q_v, fid, d = self._queue.get_nowait()
            if fid in batch:
                batch[fid][0].append(q_v)
                batch[fid] = (batch[fid][0], batch[fid][1] + d)
            else:
                batch[fid] = ([q_v], d)
            self._queue.task_done()

        return batch

    async def _apply_topological_shift(
        self, batch: dict[str, tuple[list[list[float]], float]]
    ) -> None:
        """Executes numpy topological shifts in a C-level threadpool to avoid event loop blocking."""
        if not batch:
            return

        def _mutate():
            conn = self._store._get_conn()
            now = time.time()
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")

                for fid, (query_vecs, delta_exc) in batch.items():
                    self._mutate_single_fact(cursor, fid, query_vecs, delta_exc, now)

                conn.commit()
            except (OSError, ValueError):
                conn.rollback()
                raise

        # Liberamos el GIL mientras SQLite y Numpy mutan los tensores
        async with self._store._lock:
            await asyncio.get_running_loop().run_in_executor(self._pool, _mutate)

    @staticmethod
    def _mutate_single_fact(
        cursor, fid: str, query_vecs: list[list[float]], delta_exc: float, now: float
    ) -> None:
        """Process a single fact mutation in the batch."""
        # 1. Recuperamos embedding actual y metadata L2
        cursor.execute(
            "SELECT m.success_rate, m.timestamp, v.embedding, m.rowid "
            "FROM facts_meta m JOIN vec_facts v ON m.rowid = v.rowid "
            "WHERE m.id = ?",
            (fid,),
        )
        row = cursor.fetchone()
        if not row:
            return

        stored_exc = float(row["success_rate"])
        last_ts = float(row["timestamp"])
        emb_bytes = row["embedding"]
        rowid = row["rowid"]

        # 2. Lazy Decay de la excitación actual
        time_delta = max(0.0, now - last_ts)
        current_exc = stored_exc * np.exp(-DECAY_LAMBDA * time_delta)

        # 3. Spike (Inyección de Masa)
        new_exc = min(EXCITATION_MAX, current_exc + delta_exc)

        # 4. Cálculo C/Numpy del nuevo Effective Vector (Gradient Descent 1-step)
        current_vec = np.frombuffer(emb_bytes, dtype=np.float32)

        # Mean of all query vectors in this batch for this fact
        mean_query_vec = np.mean(np.array(query_vecs, dtype=np.float32), axis=0)

        # El fact "aprende" topológicamente moviéndose hacia el vector de la pregunta
        # v_new = v_old + alpha * (query - v_old)
        shifted_vec = current_vec + LEARNING_RATE * (mean_query_vec - current_vec)

        # L2 Normalize the vector again to keep sqlite-vec happy
        norm = np.linalg.norm(shifted_vec)
        if norm > 0:
            shifted_vec = shifted_vec / norm
        new_emb_bytes = shifted_vec.astype(np.float32).tobytes()

        # 5. Commit a SQLite L2 Cache
        cursor.execute(
            "UPDATE facts_meta SET success_rate = ?, timestamp = ? WHERE id = ?",
            (new_exc, now, fid),
        )
        cursor.execute("UPDATE vec_facts SET embedding = ? WHERE rowid = ?", (new_emb_bytes, rowid))


class DynamicSemanticSpace:
    """Wraps the SovereignVectorStoreL2 to provide Read-as-Rewrite capabilities."""

    __slots__ = ("_store", "semantic_mutator")

    def __init__(self, store: SovereignVectorStoreL2) -> None:
        self._store = store
        self.semantic_mutator = SemanticMutator(store)

    async def recall_and_pulse(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        pulse_excitation: float = 20.0,
    ) -> list[Any]:
        """Recupera los vectores y emite un pulso topológico (Inversión Termodinámica)."""
        # Obtenemos el query vector para calcular la gradiente de topología
        query_vector = await self._store._encoder.encode(query)

        facts = await self._store.recall_secure(tenant_id, project_id, query, limit)

        # Inyecta masa topológica a facts útiles hacia el query_vector en O(1)
        for fact in facts:
            self.semantic_mutator.emit_pulse(
                query_vector, fact.id, excitation_delta=pulse_excitation
            )

        return facts
