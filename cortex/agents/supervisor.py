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
from typing import Any, Optional

from cortex.agents.base import BaseAgent
from cortex.agents.state import AgentStatus

logger = logging.getLogger("cortex.agents.supervisor")

DEFAULT_HEARTBEAT_TIMEOUT_S = 30.0
DEFAULT_MAX_RESTARTS = 3


@dataclass()
class AgentEntry:
    """Supervisor's internal record for a managed agent."""

    agent: BaseAgent
    task: Optional[asyncio.Task[None]] = None
    restart_count: int = 0
    max_restarts: int = DEFAULT_MAX_RESTARTS
    registered_at: float = field(default_factory=time.time)


class Supervisor:
    """Agent lifecycle manager and health monitor.

    Manages a registry of BaseAgent instances, starts/stops them
    as asyncio tasks, monitors heartbeats, and handles restarts
    with a retry budget.
    """

    def __init__(
        self,
        heartbeat_timeout_s: float = DEFAULT_HEARTBEAT_TIMEOUT_S,
    ) -> None:
        self._agents: dict[str, AgentEntry] = {}
        self._heartbeat_timeout_s = heartbeat_timeout_s
        self._monitor_task: Optional[asyncio.Task[None]] = None
        self._running = False

    # ── Registration ─────────────────────────────────────────────

    def register(
        self,
        agent: BaseAgent,
        max_restarts: int = DEFAULT_MAX_RESTARTS,
    ) -> None:
        """Register an agent for lifecycle management."""
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent '{agent.agent_id}' already registered")

        self._agents[agent.agent_id] = AgentEntry(
            agent=agent,
            max_restarts=max_restarts,
        )
        logger.info(
            "Supervisor: Registered '%s' (restarts=%d)",
            agent.agent_id,
            max_restarts,
        )

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from supervision (must be stopped first)."""
        entry = self._agents.get(agent_id)
        if entry is None:
            raise KeyError(f"Agent '{agent_id}' not registered")
        if entry.task is not None and not entry.task.done():
            raise RuntimeError(
                f"Agent '{agent_id}' is still running — stop it first"
            )
        del self._agents[agent_id]
        logger.info("Supervisor: Unregistered '%s'", agent_id)

    # ── Lifecycle ────────────────────────────────────────────────

    async def start_agent(self, agent_id: str) -> None:
        """Start a specific agent."""
        entry = self._get_entry(agent_id)
        if entry.task is not None and not entry.task.done():
            logger.warning("Supervisor: '%s' already running", agent_id)
            return

        entry.task = await entry.agent.start()
        logger.info("Supervisor: Started '%s'", agent_id)

    async def stop_agent(self, agent_id: str) -> None:
        """Gracefully stop a specific agent."""
        entry = self._get_entry(agent_id)
        if entry.task is None or entry.task.done():
            logger.warning("Supervisor: '%s' not running", agent_id)
            return

        await entry.agent.stop()

        # Wait for graceful shutdown with timeout
        try:
            await asyncio.wait_for(entry.task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(
                "Supervisor: '%s' did not stop gracefully, force-cancelling",
                agent_id,
            )
            entry.agent.force_stop()

    async def quarantine_agent(self, agent_id: str, reason: str = "") -> None:
        """Quarantine an agent — stop it and mark as quarantined."""
        entry = self._get_entry(agent_id)
        entry.agent.state.status = AgentStatus.QUARANTINED
        entry.agent.state.metadata["quarantine_reason"] = reason

        if entry.task is not None and not entry.task.done():
            entry.agent.force_stop()

        logger.warning(
            "Supervisor: QUARANTINED '%s' — %s",
            agent_id,
            reason or "no reason given",
        )

    async def restart_agent(self, agent_id: str) -> bool:
        """Restart an agent if within retry budget.

        Returns True if restarted, False if budget exhausted.
        """
        entry = self._get_entry(agent_id)

        if entry.restart_count >= entry.max_restarts:
            logger.error(
                "Supervisor: '%s' exceeded restart budget (%d/%d) — quarantining",
                agent_id,
                entry.restart_count,
                entry.max_restarts,
            )
            await self.quarantine_agent(
                agent_id,
                f"Restart budget exhausted ({entry.restart_count}/{entry.max_restarts})",
            )
            return False

        # Stop if still running
        if entry.task is not None and not entry.task.done():
            entry.agent.force_stop()
            await asyncio.sleep(0.1)

        # Reset state for restart
        entry.agent.state.status = AgentStatus.IDLE
        entry.agent.state.consecutive_errors = 0
        entry.restart_count += 1

        entry.task = await entry.agent.start()
        logger.info(
            "Supervisor: Restarted '%s' (attempt %d/%d)",
            agent_id,
            entry.restart_count,
            entry.max_restarts,
        )
        return True

    # ── Batch operations ─────────────────────────────────────────

    async def start_all(self) -> None:
        """Start all registered agents."""
        self._running = True
        for agent_id in self._agents:
            await self.start_agent(agent_id)

        # Start health monitor
        self._monitor_task = asyncio.create_task(
            self._health_monitor_loop(),
            name="supervisor-health-monitor",
        )
        logger.info("Supervisor: All %d agents started", len(self._agents))

    async def stop_all(self) -> None:
        """Stop all agents and the health monitor."""
        self._running = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        for agent_id in list(self._agents.keys()):
            try:
                await self.stop_agent(agent_id)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Supervisor: Error stopping '%s': %s", agent_id, exc
                )

        logger.info("Supervisor: All agents stopped")

    # ── Health monitoring ────────────────────────────────────────

    async def _health_monitor_loop(self) -> None:
        """Periodic health check of all managed agents."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_timeout_s / 2)
                await self.health_check()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Supervisor: Health monitor error: %s", exc)

    async def health_check(self) -> dict[str, Any]:
        """Run health check on all agents. Auto-restart failed ones."""
        report: dict[str, Any] = {}
        now = time.time()

        for agent_id, entry in self._agents.items():
            status = entry.agent.state.status
            heartbeat = entry.agent.state.last_heartbeat_ts
            task_alive = entry.task is not None and not entry.task.done()

            agent_report: dict[str, Any] = {
                "status": status.value,
                "task_alive": task_alive,
                "errors": entry.agent.state.error_count,
                "consecutive_errors": entry.agent.state.consecutive_errors,
                "messages_processed": entry.agent.state.total_messages_processed,
                "restarts": entry.restart_count,
                "last_heartbeat_age_s": (
                    round(now - heartbeat, 1) if heartbeat else None
                ),
            }

            # Detect dead agents that should be running
            if (
                status == AgentStatus.RUNNING
                and not task_alive
                and entry.restart_count < entry.max_restarts
            ):
                logger.warning(
                    "Supervisor: '%s' task died unexpectedly — restarting",
                    agent_id,
                )
                await self.restart_agent(agent_id)
                agent_report["action"] = "restarted"

            # Detect stale heartbeats
            if (
                task_alive
                and heartbeat
                and (now - heartbeat) > self._heartbeat_timeout_s
            ):
                logger.warning(
                    "Supervisor: '%s' heartbeat stale (%.1fs) — restarting",
                    agent_id,
                    now - heartbeat,
                )
                await self.restart_agent(agent_id)
                agent_report["action"] = "restarted_stale_heartbeat"

            report[agent_id] = agent_report

        return report

    # ── Status ───────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Get status of all managed agents."""
        return {
            agent_id: {
                "status": entry.agent.state.status.value,
                "errors": entry.agent.state.error_count,
                "messages": entry.agent.state.total_messages_processed,
                "restarts": entry.restart_count,
                "daemon": entry.agent.manifest.daemon,
                "last_heartbeat": entry.agent.state.last_heartbeat_ts,
            }
            for agent_id, entry in self._agents.items()
        }

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def running_count(self) -> int:
        return sum(
            1
            for e in self._agents.values()
            if e.agent.state.status == AgentStatus.RUNNING
        )

    # ── Internal ─────────────────────────────────────────────────

    def _get_entry(self, agent_id: str) -> AgentEntry:
        entry = self._agents.get(agent_id)
        if entry is None:
            raise KeyError(f"Agent '{agent_id}' not registered")
        return entry
