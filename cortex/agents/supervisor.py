"""CORTEX Agent Runtime — Supervisor.

The Supervisor manages agent lifecycle:
    - register / start / stop / quarantine
    - health monitoring via heartbeat
    - restart with retry budget
    - status reporting

This is the plano de control for the agent swarm.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from cortex.agents.state import AgentStatus

logger = logging.getLogger("cortex.agents.supervisor")

DEFAULT_HEARTBEAT_TIMEOUT_S = 30.0
DEFAULT_MAX_RESTARTS = 3


@runtime_checkable
class Supervisable(Protocol):
    """Interface for any component (Agent or Supervisor) that can be
    managed (Ω₀)."""

    @property
    def agent_id(self) -> str:
        """Unique identifier for the managed entity."""
        ...

    async def start(self) -> asyncio.Task[None]:
        """Start the entity as an asyncio Task."""
        ...

    async def stop(self) -> None:
        """Gracefully stop the entity."""
        ...

    def force_stop(self) -> None:
        """Immediately terminate the entity."""
        ...

    @property
    def status(self) -> AgentStatus:
        """Current lifecycle status."""
        ...


@dataclass()
class ManagedEntry:
    """Supervisor's internal record for a managed entity (Supervisable)."""

    entity: Supervisable
    task: Optional[asyncio.Task[None]] = None
    restart_count: int = 0
    max_restarts: int = DEFAULT_MAX_RESTARTS
    registered_at: float = field(default_factory=time.time)


class Supervisor:
    """
    Agent and Sub-Swarm lifecycle manager.

    Implements Supervisable to allow hierarchical nesting (Ω₀).
    Scaling from Swarm-100 to Swarm-10K requires recursive supervision.
    """

    def __init__(
        self,
        id: str = "root-supervisor",
        heartbeat_timeout_s: float = DEFAULT_HEARTBEAT_TIMEOUT_S,
    ) -> None:
        self._id = id
        self._managed: dict[str, ManagedEntry] = {}
        self._heartbeat_timeout_s = heartbeat_timeout_s
        self._monitor_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    @property
    def agent_id(self) -> str:
        return self._id

    @property
    def status(self) -> AgentStatus:
        if not self._running:
            return AgentStatus.IDLE
        return AgentStatus.RUNNING

    # ── Registration ─────────────────────────────────────────────

    def register(
        self,
        entity: Supervisable,
        max_restarts: int = DEFAULT_MAX_RESTARTS,
    ) -> None:
        """Register a Supervisable entity (Agent or Sub-Supervisor)."""
        if entity.agent_id in self._managed:
            raise ValueError(f"Entity '{entity.agent_id}' already registered")

        self._managed[entity.agent_id] = ManagedEntry(
            entity=entity,
            max_restarts=max_restarts,
        )
        logger.info(
            "Supervisor[%s]: Registered '%s' (restarts=%d)",
            self._id,
            entity.agent_id,
            max_restarts,
        )

    def unregister(self, entity_id: str) -> None:
        """Remove an entity from supervision."""
        entry = self._managed.get(entity_id)
        if entry is None:
            raise KeyError(f"Entity '{entity_id}' not registered")
        if entry.task is not None and not entry.task.done():
            raise RuntimeError(f"Entity '{entity_id}' is still running — stop it first")
        del self._managed[entity_id]
        logger.info("Supervisor[%s]: Unregistered '%s'", self._id, entity_id)

    def get_entity(self, entity_id: str) -> Optional[Supervisable]:
        """Recursive entity lookup (Ω₀)."""
        if entity_id in self._managed:
            return self._managed[entity_id].entity

        for entry in self._managed.values():
            if isinstance(entry.entity, Supervisor):
                found = entry.entity.get_entity(entity_id)
                if found:
                    return found
        return None

    def _get_entry(self, entity_id: str) -> ManagedEntry:
        if entity_id not in self._managed:
            raise KeyError(f"Entity '{entity_id}' not found in Supervisor '{self._id}'")
        return self._managed[entity_id]

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self) -> asyncio.Task[None]:
        """Implements Supervisable.start() for nesting."""
        if self._running:
            if self._task is None:
                self._task = asyncio.current_task()
            return self._task

        self._running = True
        await self.start_all()
        # The 'task' of a supervisor is its heartbeat monitor
        self._task = self._monitor_task
        return self._task  # type: ignore

    async def stop(self) -> None:
        """Implements Supervisable.stop() for nesting."""
        self._running = False
        await self.stop_all()

    def force_stop(self) -> None:
        """Implements Supervisable.force_stop() for nesting."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        for entry in self._managed.values():
            entry.entity.force_stop()

    async def start_entity(self, entity_id: str) -> None:
        """Start a specific managed entity."""
        entry = self._get_entry(entity_id)
        if entry.task is not None and not entry.task.done():
            logger.warning("Supervisor[%s]: '%s' already running", self._id, entity_id)
            return

        entry.task = await entry.entity.start()
        logger.info("Supervisor[%s]: Started '%s'", self._id, entity_id)

    async def stop_entity(self, entity_id: str) -> None:
        """Gracefully stop a specific managed entity."""
        entry = self._get_entry(entity_id)
        if entry.task is None or entry.task.done():
            logger.warning("Supervisor[%s]: '%s' not running", self._id, entity_id)
            return

        await entry.entity.stop()

        # Wait for graceful shutdown with timeout
        try:
            await asyncio.wait_for(entry.task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(
                "Supervisor[%s]: '%s' did not stop gracefully, force-cancelling",
                self._id,
                entity_id,
            )
            entry.entity.force_stop()

    async def restart_entity(self, entity_id: str) -> bool:
        """Restart an entity if within retry budget."""
        entry = self._get_entry(entity_id)

        if entry.restart_count >= entry.max_restarts:
            logger.error(
                "Supervisor[%s]: '%s' exceeded restart budget (%d/%d)",
                self._id,
                entity_id,
                entry.restart_count,
                entry.max_restarts,
            )
            return False

        # Stop if still running
        if entry.task is not None and not entry.task.done():
            entry.entity.force_stop()
            await asyncio.sleep(0.1)

        entry.restart_count += 1
        entry.task = await entry.entity.start()
        logger.info(
            "Supervisor[%s]: Restarted '%s' (attempt %d/%d)",
            self._id,
            entity_id,
            entry.restart_count,
            entry.max_restarts,
        )
        return True

    # ── Batch operations ─────────────────────────────────────────

    async def start_all(self) -> None:
        """Start all registered entities."""
        self._running = True
        for entity_id in self._managed:
            await self.start_entity(entity_id)

        # Start health monitor
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(
                self._health_monitor_loop(),
                name=f"supervisor-{self._id}-monitor",
            )
        logger.info(
            "Supervisor[%s]: All %d entities started",
            self._id,
            len(self._managed),
        )

    async def stop_all(self) -> None:
        """Stop all entities and the health monitor."""
        self._running = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        for entity_id in list(self._managed.keys()):
            try:
                await self.stop_entity(entity_id)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Supervisor[%s]: Error stopping '%s': %s",
                    self._id,
                    entity_id,
                    exc,
                )

        logger.info("Supervisor[%s]: All entities stopped", self._id)

    # ── Health monitoring ────────────────────────────────────────

    async def _health_monitor_loop(self) -> None:
        """Periodic health check of all managed entities."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_timeout_s / 2)
                await self.health_check()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Supervisor[%s]: Health monitor error: %s", self._id, exc)

    async def health_check(self) -> dict[str, Any]:
        """Run health check on all entities. Auto-restart failed ones."""
        report: dict[str, Any] = {}

        for entity_id, entry in self._managed.items():
            status = entry.entity.status
            task_alive = entry.task is not None and not entry.task.done()

            entity_report: dict[str, Any] = {
                "status": status.value,
                "task_alive": task_alive,
                "restarts": entry.restart_count,
            }

            # Detect dead entities that should be running
            if (
                status == AgentStatus.RUNNING
                and not task_alive
                and entry.restart_count < entry.max_restarts
            ):
                logger.warning(
                    "Supervisor[%s]: '%s' died unexpectedly — restarting",
                    self._id,
                    entity_id,
                )
                await self.restart_entity(entity_id)
                entity_report["action"] = "restarted"

            report[entity_id] = entity_report

        return report

    # ── Status ───────────────────────────────────────────────────

    def status_report(self) -> dict[str, Any]:
        """Recursive status report for the entire sub-swarm."""
        return {
            "id": self._id,
            "status": self.status.value,
            "managed_count": len(self._managed),
            "children": {eid: entry.entity.status.value for eid, entry in self._managed.items()},
        }

    @property
    def managed_count(self) -> int:
        return len(self._managed)

    # ── Internal ─────────────────────────────────────────────────


class LegionSupervisor(Supervisor):
    """Manages a sub-swarm of Centurions (Ω₀)."""

    def __init__(self, id: str) -> None:
        super().__init__(id=f"legion-{id}")


class CenturionSupervisor(Supervisor):
    """Manages a sub-swarm of Agents (Ω₀)."""

    def __init__(self, id: str) -> None:
        super().__init__(id=f"centurion-{id}")
