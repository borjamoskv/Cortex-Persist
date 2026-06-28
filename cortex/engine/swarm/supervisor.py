# [C5-REAL] Exergy-Maximized
"""
CORTEX SWARM SUPERVISOR (Hito 3) -> FABLE-5 SANEDRIN FUSION
Replaces the old L0/L1 hierarchy with a decoupled, backpressure-aware Supervisor.
Pipelines: TopologyIndex -> LegionPool -> AsyncSignalBus -> CausalStateStore

**Fable-5 Injections**:
1. Tool Reliability (Self-Verify Dry Run)
2. Steerability (Taint Binding & Forced Adherence)
3. Task Completion (Context Checkpointing to prevent Context Rot)
"""

import asyncio
import json
import logging
import sys
import uuid
from typing import Any

import aiosqlite
from pydantic import ValidationError

from cortex.config import DB_PATH
from cortex.engine.causal.taint_engine import generate_secure_taint_token
from cortex.engine.causal.topological_arbitrage import TopologyIndex
from cortex.engine.swarm.legion import AsyncSignalBus, LegionPool, SwarmAgent, SwarmSignal
from cortex.engine.swarm.state_store import CausalStateStore
from cortex.extensions.skills.autodidact.epistemology import Hypothesis

logger = logging.getLogger("cortex.engine.swarm.supervisor")


class DummyAgent(SwarmAgent):
    """Fallback agent for testing the pipeline."""

    async def execute(self, target: str) -> SwarmSignal:
        await asyncio.sleep(0.01)  # Simulate work
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={"action_hex": "0x123", "observation_hex": "0xabc", "done": True},
            metrics={"exergy": 1.0},
        )


class SwarmSupervisor:
    """Apex Controller: Decoupled orchestration of the Swarm pipeline."""

    def __init__(
        self,
        db_path: str = DB_PATH,
        agent_factory: Any = DummyAgent,
        concurrency: int = 50,
        bus_maxsize: int = 1000,
    ):
        self.db_path = db_path
        self.supervisor_id = uuid.uuid4().hex
        self.bus = AsyncSignalBus(maxsize=bus_maxsize)
        self.state_store = CausalStateStore(db_path=db_path)
        self.worker_pool = LegionPool(
            agent_factory=agent_factory, bus=self.bus, concurrency=concurrency
        )
        self._running = False
        self._db: aiosqlite.Connection | None = None
        self._topo: TopologyIndex | None = None
        self._state_worker_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Starts the components and recovers ghost state."""
        from cortex.database.core import connect_async

        self._db = await connect_async(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA busy_timeout=5000;")
        self._topo = TopologyIndex(self._db)

        # SANEDRIN VECTOR 3: Recover ghost state globally
        await self.state_store.recover_in_flight_tasks(lease_id=None)

        # Start Worker Pool
        self.worker_pool.start()

        # Start State Store Consumer with Heartbeat Monitor
        self._running = True
        self._state_worker_task = asyncio.create_task(self._heartbeat_monitor())
        logger.info(f"SwarmSupervisor initialized [Lease: {self.supervisor_id}]. Pipeline active.")

    async def _heartbeat_monitor(self) -> None:
        """SANEDRIN VECTOR 2: Monitor Consumer Loop to prevent Silent Death"""
        while self._running:
            try:
                await self._state_consumer_loop()
            except Exception as e:
                logger.critical(
                    f"HEARTBEAT FAILURE: Consumer loop crashed: {e}. Initiating Controlled Apocalypse."
                )
                self._running = False
                sys.exit(1)

    async def _state_consumer_loop(self) -> None:
        """Consumes signals from Event Bus and writes them to the State Store in batches."""
        signal_buffer = []
        MAX_BATCH_SIZE = 50
        
        while self._running:
            try:
                # Wait for up to 0.5s for a signal
                signal = await asyncio.wait_for(self.bus.consume(), timeout=0.5)
                signal_buffer.append(signal)
            except asyncio.TimeoutError:
                pass # Time to flush if anything is in the buffer
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"State consumer encountered error: {e}")
                raise

            # Flush condition: buffer full, or queue is empty and we have items
            if len(signal_buffer) >= MAX_BATCH_SIZE or (signal_buffer and self.bus._queue.empty()):
                try:
                    await self.state_store.process_signals_batch(signal_buffer)
                    for _ in signal_buffer:
                        self.bus.task_done()
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    raise
                finally:
                    signal_buffer.clear()

    async def dispatch_optimal_hypotheses(self, count: int = 100) -> int:
        """Pulls optimal tasks from TopologyIndex and pushes them to Worker Pool."""
        if not self._topo or not self._db:
            raise RuntimeError("Supervisor not initialized")

        await self.state_store.sweep_expired_leases()
        await self._topo.sync()
        dispatched = 0
        in_flight = set()

        for _ in range(count):
            task = self._topo.get_next_optimal_task(in_flight)
            if not task:
                break

            try:
                # EPISTEMIC GATEKEEPER (Sanedrin-Autodidact Fusion)
                try:
                    payload_raw = task.get("statement", task.get("payload"))
                    if not payload_raw:
                        async with self._db.execute(
                            "SELECT statement FROM system_hypotheses WHERE id = ?", (task["id"],)
                        ) as cur:
                            row = await cur.fetchone()
                            payload_raw = row[0] if row else "{}"
                    payload_dict = (
                        json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                    )

                    # FABLE 5 SIGNAL 2: Steerability Constraint Injection (Strict Epistemic Gatekeeper)
                    # Offload CPU-bound cryptography to a thread to prevent Event Loop Starvation
                    taint_token = await asyncio.to_thread(
                        generate_secure_taint_token,
                        agent_id="sanedrin_apex",
                        session_id=self.supervisor_id,
                        content=str(task["id"]),
                        private_key_b64="dGVzdF9rZXlfdGVzdF9rZXlfdGVzdF9rZXlfdGVzdF8=",
                    )
                    payload_dict["_steerability_taint"] = taint_token
                    payload_dict["_forced_tool_choice"] = "auto"

                    Hypothesis.model_validate(payload_dict)

                except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as epi_err:
                    logger.warning(
                        f"[EpistemicBreaker] Task {task['id']} rejected (Fable-Verify Failure): {epi_err}"
                    )
                    from cortex.database.core import causal_write

                    with causal_write(self._db):
                        await self._db.execute(
                            "UPDATE system_hypotheses SET status = 'INVALIDATED' WHERE id = ?",
                            (task["id"],),
                        )
                        await self._db.commit()
                    in_flight.add(task["id"])
                    continue

                # VECTOR 1 REMEDIATION: Pre-check queue capacity to eliminate Phantom Lease Burns
                if self.worker_pool._queue.full():
                    logger.warning("Thermodynamic Pause: Worker Queue is full. Halting dispatch loop.")
                    break

                # SANEDRIN VECTOR 3: Lease lock task using supervisor_id and 5-min TTL
                from datetime import datetime, timedelta, timezone

                from cortex.database.core import causal_write

                expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
                with causal_write(self._db):
                    await self._db.execute(
                        "UPDATE system_hypotheses SET status = 'IN_FLIGHT', owner_id = ?, lease_expires_at = ? WHERE id = ?",
                        (self.supervisor_id, expires_at, task["id"]),
                    )
                    await self._db.commit()

                try:
                    # Non-blocking dispatch
                    self.worker_pool.dispatch_nowait(task["id"])
                    in_flight.add(task["id"])
                    dispatched += 1
                except asyncio.QueueFull:
                    logger.critical("Queue filled between pre-check and dispatch. Reverting lease.")
                    # Phantom Lease Rollback (Fail-safe)
                    with causal_write(self._db):
                        await self._db.execute(
                            "UPDATE system_hypotheses SET status = 'PENDING', owner_id = NULL, lease_expires_at = NULL WHERE id = ?",
                            (task["id"],),
                        )
                        await self._db.commit()
                    break
                except Exception as e:
                    logger.error(
                        f"Dispatch failed for task {task['id']}. Rolling back lease. Error: {e}"
                    )
                    with causal_write(self._db):
                        await self._db.execute(
                            "UPDATE system_hypotheses SET status = 'PENDING', owner_id = NULL, lease_expires_at = NULL WHERE id = ?",
                            (task["id"],),
                        )
                        await self._db.commit()
            except Exception as e:
                logger.error(f"Critical dispatch loop failure for task {task['id']}: {e}")

        if dispatched > 0:
            logger.info(f"Dispatched {dispatched} optimal hypotheses with Fable 5 Steerability.")

        return dispatched

    async def shutdown(self) -> None:
        """Gracefully shutdown the pipeline."""
        self._running = False
        await self.worker_pool.stop()

        if self._state_worker_task:
            await self._state_worker_task

        await self.state_store.close()

        if self._db:
            await self._db.close()
            self._db = None

        logger.info("SwarmSupervisor shutdown complete.")
