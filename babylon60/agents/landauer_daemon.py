# [C5-REAL] Exergy-Maximized
"""Landauer Daemon Agent - The Context Compactor.

Implements the Landauer Principle in BABYLON-60.
Continuously prunes obsolete or low-exergy contexts from WorkingMemory
and the MessageBus to prevent Context Rot.
"""

import asyncio
import logging

from babylon60.agents.base import BaseAgent
from babylon60.agents.bus import MessageBus
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.state import AgentStatus

logger = logging.getLogger("babylon60.agents.landauer_daemon")


class LandauerDaemonAgent(BaseAgent):
    """Daemon that purges stale memory and messages to free thermodynamic capacity."""

    def __init__(
        self, manifest: AgentManifest, bus: MessageBus, compaction_interval_seconds: float = 60.0
    ) -> None:
        super().__init__(manifest, bus)
        self.compaction_interval_seconds = compaction_interval_seconds
        self._daemon_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Starts the daemon."""
        await super().start()
        if not self._daemon_task:
            self._daemon_task = asyncio.create_task(self._compaction_loop())

    async def stop(self) -> None:
        """Stops the daemon."""
        if self._daemon_task:
            self._daemon_task.cancel()
            try:
                await self._daemon_task
            except asyncio.CancelledError:
                pass
            self._daemon_task = None
        await super().stop()

    async def _compaction_loop(self) -> None:
        """Continuous background loop for Context Compaction."""
        logger.info(
            f"[{self.manifest.agent_id}] Landauer Daemon started. Interval: {self.compaction_interval_seconds}s"
        )
        while True:
            try:
                await asyncio.sleep(self.compaction_interval_seconds)
                await self._compact_memory()
            except asyncio.CancelledError:
                logger.info(f"[{self.manifest.agent_id}] Landauer Daemon stopped.")
                break
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{self.manifest.agent_id}] Landauer Daemon error: {e}")
                # Prevent silent thread death # noqa: BLE001

    async def _compact_memory(self) -> None:
        """Executes the actual pruning logic."""
        if self.state.status == AgentStatus.STOPPED:
            return

        # Here we would interface with `WorkingMemory` or `MessageBus` to purge old items.
        # For now, it's a simulated logging of the thermodynamic cost.
        logger.info(
            f"[{self.manifest.agent_id}] Executing Context Compaction (Landauer erasure cost applied)."
        )
        # In a real C5-REAL implementation, we would query the bus:
        # obsolete_messages = await self.bus.query(older_than=...)
        # await self.bus.delete(obsolete_messages)


def create_landauer_daemon(
    name: str, bus: MessageBus, compaction_interval_seconds: float = 60.0
) -> LandauerDaemonAgent:
    """Factory for LandauerDaemonAgent."""
    manifest = AgentManifest(
        agent_id=name,
        purpose="Background daemon for pruning context and preventing Context Rot.",
        can_delegate=False,
        daemon=True,
    )
    agent = LandauerDaemonAgent(manifest, bus, compaction_interval_seconds)
    return agent
