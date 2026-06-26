# [C5-REAL] Exergy-Maximized
"""
CORTEX SWARM SUPERVISOR (Hito 3)
Replaces the old L0/L1 hierarchy with a decoupled, backpressure-aware Supervisor.
Pipelines: TopologyIndex -> LegionPool -> AsyncSignalBus -> CausalStateStore
"""

import asyncio
import logging
import uuid
import sys
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
from cortex.engine.causal.topological_arbitrage import TopologyIndex
from cortex.engine.swarm.legion import AsyncSignalBus, LegionPool, SwarmAgent, SwarmSignal
from cortex.engine.swarm.state_store import CausalStateStore

logger = logging.getLogger("cortex.engine.swarm.supervisor")

class DummyAgent(SwarmAgent):
    """Fallback agent for testing the pipeline."""
    async def execute(self, target: str) -> SwarmSignal:
        await asyncio.sleep(0.01) # Simulate work
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={"action_hex": "0x123", "observation_hex": "0xabc", "done": True},
            metrics={"exergy": 1.0}
        )

class SwarmSupervisor:
    """Apex Controller: Decoupled orchestration of the Swarm pipeline."""

    def __init__(self, db_path: str = DB_PATH, agent_factory: Any = DummyAgent, concurrency: int = 50, bus_maxsize: int = 1000):
        self.db_path = db_path
        self.supervisor_id = uuid.uuid4().hex
        self.bus = AsyncSignalBus(maxsize=bus_maxsize)
        self.state_store = CausalStateStore(db_path=db_path)
        self.worker_pool = LegionPool(agent_factory=agent_factory, bus=self.bus, concurrency=concurrency)
        self._running = False
        self._db: aiosqlite.Connection | None = None
        self._topo: TopologyIndex | None = None
        self._state_worker_task: asyncio.Task | None = None
        
    async def initialize(self) -> None:
        """Starts the components and recovers ghost state."""
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL;")
        self._topo = TopologyIndex(self._db)
        
        # SANEDRIN VECTOR 3: Recover ghost state globally
        # (Assuming single L0 restart sweep, otherwise pass supervisor_id)
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
                logger.critical(f"HEARTBEAT FAILURE: Consumer loop crashed: {e}. Initiating Controlled Apocalypse.")
                self._running = False
                sys.exit(1)

    async def _state_consumer_loop(self) -> None:
        """Consumes signals from Event Bus and writes them to the State Store."""
        while self._running:
            try:
                # Use a timeout so we can exit gracefully
                signal = await asyncio.wait_for(self.bus.consume(), timeout=1.0)
                await self.state_store.process_signal(signal)
                self.bus.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"State consumer encountered error: {e}")
                raise  # Re-raise for Heartbeat

    async def dispatch_optimal_hypotheses(self, count: int = 100) -> int:
        """Pulls optimal tasks from TopologyIndex and pushes them to Worker Pool."""
        if not self._topo or not self._db:
            raise RuntimeError("Supervisor not initialized")
            
        await self._topo.sync()
        dispatched = 0
        in_flight = set()

        for _ in range(count):
            task = self._topo.get_next_optimal_task(in_flight)
            if not task:
                break
                
            try:
                # SANEDRIN VECTOR 3: Lease lock task using supervisor_id
                await self._db.execute(
                    "UPDATE system_hypotheses SET status = 'IN_FLIGHT', owner_id = ? WHERE id = ?", 
                    (self.supervisor_id, task["id"])
                )
                await self._db.commit()
                
                # Push to worker pool
                await self.worker_pool.dispatch(task["id"])
                in_flight.add(task["id"])
                dispatched += 1
            except asyncio.QueueFull:
                logger.warning("Thermodynamic Pause: Worker Queue is full. Backpressure applied.")
                break
            except Exception as e:
                logger.error(f"Dispatch failed for task {task['id']}: {e}")
                
        if dispatched > 0:
            logger.info(f"Dispatched {dispatched} optimal hypotheses.")
            
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
