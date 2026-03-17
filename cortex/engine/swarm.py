"""
CORTEX-SWARM-100: Sovereign Swarm Architecture
Implements the 100-parallel agent P2P loop: MAP, SHARD, SYNC (AsyncSignalBus), CRYSTALLIZE.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


@dataclass
class SwarmSignal:
    """A signal emitted by an agent to the AsyncSignalBus."""

    agent_id: str
    target: str
    status: str  # e.g., "SUCCESS", "FAILURE", "VOID"
    payload: dict[str, Any]
    metrics: dict[str, Any]


class AsyncSignalBus:
    """Collision-free message bus for inter-agent communication (SYNC phase)."""

    def __init__(self) -> None:
        self._signals: list[SwarmSignal] = []
        self._lock = asyncio.Lock()
        self._active_agents = 0
        self._finished_event = asyncio.Event()

    async def emit(self, signal: SwarmSignal) -> None:
        """Agents call this to drop a signal on the bus."""
        async with self._lock:
            # Enforce VOID invariant: Drop empty signals immediately
            if not signal.payload and signal.status != "VOID":
                logger.warning(
                    "SwarmAgent[%s] emitted empty payload without VOID.", signal.agent_id
                )
                signal.status = "VOID"

            self._signals.append(signal)
            logger.debug("Bus received signal from %s: %s", signal.agent_id, signal.status)

    async def get_all(self) -> list[SwarmSignal]:
        """Called by the commander (Squadron) during CRYSTALLIZE."""
        async with self._lock:
            return list(self._signals)


class SwarmAgent(ABC):
    """Base class for a virtual agent operating inside the swarm."""

    def __init__(self, agent_id: str, bus: AsyncSignalBus, engine: Any = None):
        self.agent_id = agent_id
        self.bus = bus
        self.engine = engine  # Reference to CortexEngine if needed

    async def run(self, queue: asyncio.Queue[str]) -> None:
        """Consumes shards from the queue, executes the mission, and emits signals."""
        while True:
            try:
                target = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            logger.info("Agent [%s] executing on target: %s", self.agent_id, target)
            try:
                signal = await self.execute(target)
                await self.bus.emit(signal)
            except Exception as e:  # noqa: BLE001
                logger.error("Agent [%s] failed on %s: %s", self.agent_id, target, e)
                await self.bus.emit(
                    SwarmSignal(
                        agent_id=self.agent_id,
                        target=target,
                        status="FAILURE",
                        payload={"error": str(e)},
                        metrics={},
                    )
                )
            finally:
                queue.task_done()

    @abstractmethod
    async def execute(self, target: str) -> SwarmSignal:
        """Subclasses must implement the actual kinetic/integrity logic here."""
        pass


class Squadron(ABC):
    """
    Orchestrates the P2P Loop:
    1. MAP: Generates targets.
    2. SHARD: Distributes to N agents.
    3. SYNC: Awaits the bus.
    4. CRYSTALLIZE: Consolidates signals.
    """

    # Squadron configurations
    SQUAD_NAME: ClassVar[str] = "BASE"
    REPLICAS: ClassVar[int] = 1

    def __init__(self, engine: Any = None):
        self.engine = engine
        self.bus = AsyncSignalBus()
        self.agents: list[SwarmAgent] = []

    @abstractmethod
    def _create_agent(self, agent_id: str) -> SwarmAgent:
        """Spawn a specific type of agent."""
        pass

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        """MAP phase: Returns a list of targets (e.g., file paths, API endpoints)."""
        return [target_pattern] if target_pattern else []

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        """CRYSTALLIZE phase: Aggregate signals. Subclasses may write to the Ledger here."""
        success_count = sum(1 for s in signals if s.status == "SUCCESS")
        void_count = sum(1 for s in signals if s.status == "VOID")

        report = {
            "squadron": self.SQUAD_NAME,
            "total_signals": len(signals),
            "success": success_count,
            "voids": void_count,
            "raw": [
                {"target": s.target, "status": s.status, "payload": s.payload} for s in signals
            ],
        }

        # Enforce COMPACT invariant: Log final aggregation briefly
        logger.info(
            "💎 [CRYSTALLIZE] Squadron %s finished: %d Targets, %d Success, %d Voids",
            self.SQUAD_NAME,
            len(signals),
            success_count,
            void_count,
        )

        return report

    async def deploy(self, target_pattern: str | None = None) -> dict[str, Any]:
        """Executes the full P2P deployment loop."""
        logger.info(
            "🚀 [SWARM] Deploying %s Squadron (%d concurrent agents)...",
            self.SQUAD_NAME,
            self.REPLICAS,
        )

        # 1. MAP
        targets = await self._map(target_pattern)
        if not targets:
            logger.warning("[MAP] No targets for: %s. Aborting.", target_pattern)
            return {"error": "No targets"}

        # 2. SHARD
        queue: asyncio.Queue[str] = asyncio.Queue()
        for t in targets:
            queue.put_nowait(t)

        # Construct agents
        self.agents = [
            self._create_agent(f"{self.SQUAD_NAME}-{i:03d}") for i in range(self.REPLICAS)
        ]

        # 3. SYNC
        tasks = [asyncio.create_task(agent.run(queue)) for agent in self.agents]
        await queue.join()  # Wait until queue is drained
        await asyncio.gather(*tasks)  # Ensure all tasks finish

        # 4. CRYSTALLIZE
        signals = await self.bus.get_all()
        return await self._crystallize(signals)
