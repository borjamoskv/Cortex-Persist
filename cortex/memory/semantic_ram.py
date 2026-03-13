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
from typing import TYPE_CHECKING, Any, Final, TypedDict

import numpy as np


class SemanticFactPayload(TypedDict):
    """Payload representing a fact transiting through working towards semantic memory."""

    project: str
    content: str
    fact_type: str
    timestamp: str


from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2  # noqa: E402

__all__ = ["DynamicSemanticSpace", "SemanticMutator"]

logger = logging.getLogger("cortex.memory.semantic_ram")

# Import topological health types (lazy to avoid circular imports)
if TYPE_CHECKING:
    from cortex.memory.manager import CortexMemoryManager
    from cortex.memory.models import CortexFactModel
    from cortex.memory.topological_health import (
        TopologicalAnchor,
        TopologicalHealthMonitor,
    )

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

    __slots__ = ("_store", "_queue", "_worker_task", "_pool", "_health_monitor", "_anchor")

    def __init__(
        self,
        store: SovereignVectorStoreL2,
        health_monitor: TopologicalHealthMonitor | None = None,
        anchor: TopologicalAnchor | None = None,
    ) -> None:
        self._store = store
        self._queue: asyncio.Queue[tuple[list[float], str, float]] = asyncio.Queue(maxsize=10000)
        self._worker_task: asyncio.Task[None] | None = None
        # ThreadPoolExecutor to bypass Python GIL during Numpy topological operations
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ctx_mutator")
        # Topological health write-gate: skip mutations if model_hash has drifted
        self._health_monitor = health_monitor
        self._anchor = anchor

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
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("SemanticMutator shutdown error: %s", e)
            self._pool.shutdown(wait=True)
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
                raise
            except (OSError, RuntimeError, ValueError) as e:
                logger.error("SemanticMutator: Pulse mutation failed: %s", e)
                await asyncio.sleep(1.0)

    async def _collect_batch(self) -> dict[str, tuple[list[list[float]], float]]:
        """Collect and aggregate pulses into a batch before applying topological shifts."""
        batch: dict[str, tuple[list[list[float]], float]] = {}

        query_vec, fact_id, delta = await self._queue.get()
        batch[fact_id] = ([query_vec], delta)
        self._queue.task_done()

        # LEGION-OMEGA (The OOM Killer): Límite doble,
        # por keys únicas (100) y por sub-items totales (500)
        total_items = 1
        while len(batch) < 100 and total_items < 500 and not self._queue.empty():
            q_v, fid, d = self._queue.get_nowait()
            if fid in batch:
                batch[fid][0].append(q_v)
                batch[fid] = (batch[fid][0], batch[fid][1] + d)
            else:
                batch[fid] = ([q_v], d)
            self._queue.task_done()
            total_items += 1

        return batch

    async def _apply_topological_shift(
        self, batch: dict[str, tuple[list[list[float]], float]]
    ) -> None:
        """Executes numpy topological shifts in a
        C-level threadpool to avoid event loop blocking.
        """
        if not batch:
            return

        # WRITE-GATE: If health monitor detects model_hash drift, skip batch.
        # Fail-safe, not fail-deadly — log CRITICAL but don't crash.
        if self._health_monitor and self._anchor:
            if self._health_monitor.needs_recalibration(self._anchor):
                logger.critical(
                    "SemanticMutator: MODEL HASH DRIFT. "
                    "Anchor=%s, current=%s. "
                    "Skipping %d mutations.",
                    self._anchor.model_hash[:12],
                    self._health_monitor._model_hash[:12],
                    len(batch),
                )
                return

        def _mutate():
            # LEGION-OMEGA (Chronos Sniper): Evitar deadlock, manejar sqlite3.Error general
            # (vía Exception genérico controlado)
            conn = self._store._get_conn()
            now = time.time()
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")

                self._mutate_batch(cursor, batch, now)

                conn.commit()
            except Exception as e:  # noqa: BLE001
                # Si una DB lock o constraint quiebra la query, asegura rollback de BEGIN IMMEDIATE
                conn.rollback()
                logger.error("SemanticMutator: Unrecoverable mutation error: %s", e)
                raise

        # Liberamos el GIL mientras SQLite y Numpy mutan los tensores
        async with self._store._lock:
            await asyncio.get_running_loop().run_in_executor(self._pool, _mutate)

    @staticmethod
    def _mutate_batch(
        cursor, batch: dict[str, tuple[list[list[float]], float]], now: float
    ) -> None:
        """Process all fact mutations in a single vectorized sweep. O(1) DB roundtrips."""
        keys = list(batch.keys())
        placeholders = ",".join(["?"] * len(keys))

        cursor.execute(
            f"SELECT m.id, m.success_rate, m.timestamp, v.embedding, m.rowid "
            f"FROM facts_meta m JOIN vec_facts v ON m.rowid = v.rowid "
            f"WHERE m.id IN ({placeholders})",
            keys,
        )
        rows = cursor.fetchall()

        meta_updates = []
        vec_updates = []

        for row in rows:
            fid = row["id"]
            if fid not in batch:
                continue

            query_vecs, delta_exc = batch[fid]
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
            mean_query_vec = np.mean(np.array(query_vecs, dtype=np.float32), axis=0)

            shifted_vec = current_vec + LEARNING_RATE * (mean_query_vec - current_vec)
            norm = np.linalg.norm(shifted_vec)
            if norm > 0:
                shifted_vec = shifted_vec / norm

            meta_updates.append((new_exc, now, fid))
            vec_updates.append((shifted_vec.astype(np.float32).tobytes(), rowid))

        # 5. Commit Masivo vía executemany (100x más rápido en I/O)
        if meta_updates:
            cursor.executemany(
                "UPDATE facts_meta SET success_rate = ?, timestamp = ? WHERE id = ?",
                meta_updates,
            )
            cursor.executemany(
                "UPDATE vec_facts SET embedding = ? WHERE rowid = ?",
                vec_updates,
            )


class AutonomicMemoryBuffer:
    """High-frequency temporary storage for active facts (Short-Term Memory).

    Items in this buffer are 'alive' but not yet 'immortal' (not in the ledger).
    The buffer periodically flushes to the CORTEX ledger to ensure durability
    without blocking the real-time execution loop.
    """

    def __init__(self, capacity: int = 100, pressure_threshold: float = 0.8) -> None:
        self._buffer: list[SemanticFactPayload] = []
        self._capacity = capacity
        self._pressure_threshold = pressure_threshold

    def add(self, fact_data: SemanticFactPayload) -> bool:
        """Add a fact to the autonomic buffer and check semantic pressure.
        O(1) Synchronous list operations inside asyncio are naturally thread-safe
        since the event loop is single-threaded between 'awaits'.
        """
        if len(self._buffer) >= self._capacity:
            return False
        self._buffer.append(fact_data)

        # 150/100: Return True if threshold met to trigger autonomous flush
        pressure = len(self._buffer) / self._capacity
        return pressure >= self._pressure_threshold

    def flush(self) -> list[SemanticFactPayload]:
        """Retrieve and clear all facts from the buffer (Systole)."""
        if not self._buffer:
            return []
        data = self._buffer
        self._buffer = []
        return data


class DynamicSemanticSpace:
    """Wraps the SovereignVectorStoreL2 to provide Read-as-Rewrite capabilities."""

    def __init__(
        self,
        store: SovereignVectorStoreL2,
        health_monitor: TopologicalHealthMonitor | None = None,
        anchor: TopologicalAnchor | None = None,
        buffer_capacity: int = 100,
        manager: CortexMemoryManager | None = None,
    ) -> None:
        self._store = store
        self.manager = manager
        self.semantic_mutator = SemanticMutator(store, health_monitor=health_monitor, anchor=anchor)
        self.autonomic_buffer = AutonomicMemoryBuffer(capacity=buffer_capacity)
        self._active_flushes: set[asyncio.Task[Any]] = set()
        self._heartbeat_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Starts the semantic mutator and the autonomic heartbeat."""
        self.semantic_mutator.start()
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("DynamicSemanticSpace: Autonomic heartbeat stabilized (Started).")

    async def stop(self) -> None:
        """Gracefully stops all autonomic processes."""
        await self.semantic_mutator.stop()
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("DynamicSemanticSpace shutdown error: %s", e)
            logger.info("DynamicSemanticSpace: Autonomic heartbeat collapsed (Stopped).")

    async def _heartbeat_loop(self) -> None:
        """Periodically flushes the autonomic buffer to the ledger (Autonomous Heartbeat)."""
        while True:
            try:
                await asyncio.sleep(60.0)  # Standard Heartbeat frequency
                await self.force_autonomic_flush(reason="Standard Heartbeat")
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("DynamicSemanticSpace: Heartbeat failure: %s", e)

    async def force_autonomic_flush(self, reason: str = "Unknown") -> None:
        """Forces a buffer flush and integration into the persistent ledger."""
        await asyncio.sleep(0)  # Yield to event loop to keep the function fully async
        data = self.autonomic_buffer.flush()
        if data:
            logger.info(
                "DynamicSemanticSpace: Autonomous Flush (%d facts) - Reason: %s", len(data), reason
            )
            # 150/100 Standard: Predictive persistence (systole)
            if self.manager:
                for fact in data:
                    # Async background storage tracked in _active_flushes to prevent premature GC
                    _t = asyncio.create_task(
                        self.manager.store(
                            tenant_id="default_tenant",  # Should be passed in real scenarios
                            project_id=fact["project"],
                            content=fact["content"],
                            fact_type=fact["fact_type"],
                            metadata={"source": "autonomic_heartbeat", "ts": fact["timestamp"]},
                        )
                    )
                    self._active_flushes.add(_t)
                    _t.add_done_callback(self._active_flushes.discard)

    async def recall_and_pulse(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        pulse_excitation: float = 20.0,
        layer: str | None = None,
    ) -> list[CortexFactModel]:
        """Recupera los vectores y emite un pulso topológico (Inversión Termodinámica)."""
        # Obtenemos el query vector para calcular la gradiente de topología
        query_vector = await self._store._encoder.encode(query)

        facts = await self._store.recall_secure(
            tenant_id=tenant_id, project_id=project_id, query=query, limit=limit, layer=layer
        )

        # Inyecta masa topológica a facts útiles hacia el query_vector en O(1)
        for fact in facts:
            self.semantic_mutator.emit_pulse(
                query_vector, fact.id, excitation_delta=pulse_excitation
            )

        return facts

    async def store_with_heartbeat(
        self, project: str, content: str, fact_type: str = "knowledge"
    ) -> bool:
        """Stores a fact and triggers autonomous flush if semantic pressure is high (150/100)."""
        await asyncio.sleep(0)  # Yield to event loop
        fact_data: SemanticFactPayload = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "timestamp": str(time.time()),
        }
        needs_flush = self.autonomic_buffer.add(fact_data)
        if needs_flush:
            # Autonomous trigger: Pressure threshold reached (Ω₅ Antifragile persistence)
            _t = asyncio.create_task(self.force_autonomic_flush(reason="High Semantic Pressure"))
            self._active_flushes.add(_t)
            _t.add_done_callback(self._active_flushes.discard)
        return True
