# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Supervisor.

The Supervisor manages agent lifecycle:
    - register / start / stop / quarantine
    - health monitoring via heartbeat
    - restart with retry budget
    - status reporting

This is the plano de control for the agent swarm.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from babylon60.agents.base import BaseAgent
from babylon60.agents.state import AgentStatus

logger = logging.getLogger("babylon60.agents.supervisor")

DEFAULT_HEARTBEAT_TIMEOUT_S = 30.0
DEFAULT_MAX_RESTARTS = 3


@dataclass()
class AgentEntry:
    """Supervisor's internal record for a managed agent."""

    agent: BaseAgent
    task: asyncio.Task[None] | None = None
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
        self._monitor_task: asyncio.Task[None] | None = None
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
            raise RuntimeError(f"Agent '{agent_id}' is still running - stop it first")
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
        """Quarantine an agent - stop it and mark as quarantined."""
        entry = self._get_entry(agent_id)
        entry.agent.state.status = AgentStatus.QUARANTINED
        entry.agent.state.metadata["quarantine_reason"] = reason

        if entry.task is not None and not entry.task.done():
            entry.agent.force_stop()

        logger.warning(
            "Supervisor: QUARANTINED '%s' - %s",
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
                "Supervisor: '%s' exceeded restart budget (%d/%d) - quarantining",
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
            except Exception as exc:  # noqa: BLE001
                logger.warning("Suppressed exception: %s", exc)

        for agent_id in list(self._agents.keys()):
            try:
                await self.stop_agent(agent_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("Supervisor: Error stopping '%s': %s", agent_id, exc)

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
        now = time.monotonic()

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
                "last_heartbeat_age_s": (round(now - heartbeat, 1) if heartbeat else None),
            }

            # Detect dead agents that should be running
            if (
                status == AgentStatus.RUNNING
                and not task_alive
                and entry.restart_count < entry.max_restarts
            ):
                logger.warning(
                    "Supervisor: '%s' task died unexpectedly - restarting",
                    agent_id,
                )
                await self.restart_agent(agent_id)
                agent_report["action"] = "restarted"

            # Detect stale heartbeats
            if task_alive and heartbeat and (now - heartbeat) > self._heartbeat_timeout_s:
                logger.warning(
                    "Supervisor: '%s' heartbeat stale (%.1fs) - restarting",
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
        return sum(1 for e in self._agents.values() if e.agent.state.status == AgentStatus.RUNNING)

    # ── Internal ─────────────────────────────────────────────────

    def _get_entry(self, agent_id: str) -> AgentEntry:
        entry = self._agents.get(agent_id)
        if entry is None:
            raise KeyError(f"Agent '{agent_id}' not registered")
        return entry


class EvolutionSupervisor(Supervisor):
    """Supervisor that runs an agent inside a multipass autonomous evolution loop.

    Integrates pre_eval and post_eval metrics for quality checking.
    Consolidates state anomalies / daydreams on exit.
    """

    async def run_autonomous_loop(
        self,
        agent_id: str,
        objective: str,
        pre_eval: Callable[[], Any] | None = None,
        post_eval: Callable[[], Any] | None = None,
        max_passes: int = 3,
        tenant_id: str = "default",
        dream_engine: Any = None,
    ) -> dict[str, Any]:
        """Execute a multipass loop of agent objective execution with pre/post-eval metrics.

        On exit, triggers the memory dream/consolidation cycle (AutoDream integration).
        """
        logger.info(
            "🔄 Starting Evolution Loop for agent '%s' (Objective: '%s', passes=%d)",
            agent_id,
            objective,
            max_passes,
        )

        entry = self._get_entry(agent_id)
        agent = entry.agent

        trace = []
        success = False

        for run_pass in range(1, max_passes + 1):
            logger.info("👉 Evolution Loop Pass %d/%d", run_pass, max_passes)

            # ── 1. Pre-eval ──
            pre_metrics = {}
            if pre_eval is not None:
                try:
                    if inspect.iscoroutinefunction(pre_eval):
                        pre_metrics = await pre_eval()
                    else:
                        pre_metrics = pre_eval()
                    logger.info("   [PRE-EVAL] Metrics: %s", pre_metrics)
                except Exception as exc:  # noqa: BLE001
                    logger.error("   [PRE-EVAL] Failed: %s", exc)
                    pre_metrics = {"error": str(exc)}

            # ── 2. Run agent execution ──
            exec_result = {}
            execute_fn = getattr(agent, "execute_objective", None)
            if execute_fn is not None:
                try:
                    exec_result = await execute_fn(objective)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("   [EXECUTION] Agent objective execution failed")
                    exec_result = {"status": "FAILED", "error": str(exc)}
            else:
                logger.warning("   [EXECUTION] Agent does not have execute_objective method")
                exec_result = {"status": "FAILED", "error": "Agent lacks execute_objective method"}

            # ── 3. Post-eval ──
            post_metrics = {}
            if post_eval is not None:
                try:
                    if inspect.iscoroutinefunction(post_eval):
                        post_metrics = await post_eval()
                    else:
                        post_metrics = post_eval()
                    logger.info("   [POST-EVAL] Metrics: %s", post_metrics)
                except Exception as exc:  # noqa: BLE001
                    logger.error("   [POST-EVAL] Failed: %s", exc)
                    post_metrics = {"error": str(exc)}

            # Record this pass
            pass_record = {
                "pass": run_pass,
                "pre_metrics": pre_metrics,
                "exec_result": exec_result,
                "post_metrics": post_metrics,
            }
            trace.append(pass_record)

            # Determine early exit if objective is met
            # Condition 1: post_eval indicates success
            if post_eval is not None and post_metrics.get("success", False):
                logger.info(
                    "✅ Evolution Loop succeeded early on pass %d: post_eval signaled success",
                    run_pass,
                )
                success = True
                break

            # Condition 2: Agent execution succeeded and no post_eval succeeded/existed
            if post_eval is None and exec_result.get("status") == "SUCCESS":
                logger.info(
                    "✅ Evolution Loop succeeded on pass %d: agent execution finished successfully",
                    run_pass,
                )
                success = True
                break

        # ── 4. AutoDream Integration on Exit ──
        dream_report = {}
        if dream_engine is not None:
            logger.info("💤 Initiating AutoDream Integration on Evolution Loop exit...")
            try:
                if hasattr(dream_engine, "dream_cycle"):
                    # AssociativeDreamEngine
                    dream_result = await dream_engine.dream_cycle(tenant_id=tenant_id)
                    dream_report = {
                        "status": "COMPLETED",
                        "clusters_found": getattr(dream_result, "clusters_found", 0),
                        "bridges_created": getattr(dream_result, "bridges_created", 0),
                        "engrams_reweighted": getattr(dream_result, "engrams_reweighted", 0),
                        "duration_ms": getattr(dream_result, "duration_ms", 0.0),
                    }
                elif hasattr(dream_engine, "run_full_cycle"):
                    # SleepOrchestrator
                    sleep_report = await dream_engine.run_full_cycle(tenant_id=tenant_id)
                    dream_report = {
                        "status": "COMPLETED",
                        "nrem_merged": sleep_report.nrem_merged,
                        "nrem_reinforced": sleep_report.nrem_reinforced,
                        "rem_clusters_found": sleep_report.rem_clusters_found,
                        "rem_bridges_created": sleep_report.rem_bridges_created,
                        "total_duration_ms": sleep_report.total_duration_ms,
                    }
                else:
                    logger.warning(
                        "   [AutoDream] dream_engine lacks standard run_full_cycle or dream_cycle method"
                    )
                    dream_report = {
                        "status": "SKIPPED",
                        "reason": "Unsupported dream engine interface",
                    }
                logger.info("💤 AutoDream consolidation finished: %s", dream_report)
            except Exception as exc:  # noqa: BLE001
                logger.error("❌ [AutoDream] Consolidation failed: %s", exc)
                dream_report = {"status": "FAILED", "error": str(exc)}
        else:
            logger.info("💤 AutoDream skipped: no dream engine provided")
            dream_report = {"status": "SKIPPED", "reason": "No dream engine provided"}

        return {
            "status": "SUCCESS" if success else "FAILED",
            "passes_executed": len(trace),
            "trace": trace,
            "dream_integration": dream_report,
        }
