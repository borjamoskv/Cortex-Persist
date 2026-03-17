"""CORTEX v7.0 — Agent Manager (The Capataz).

Orchestrates multi-agent dialectics. The Foreman manages parallel
workstreams for Research, Implementation, and Verification.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.swarm.budget import get_budget_manager

logger = logging.getLogger("cortex.swarm.manager")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SwarmTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Anonymous Task"
    agent_name: str = "UniversalAgent"
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None


class CapatazOrchestrator:
    """The Capataz (Foreman). Coordinates a polyphony of agents."""

    def __init__(self, mission_id: str | None = None):
        self.mission_id = mission_id or f"mission-{uuid.uuid4().hex[:8]}"
        self.tasks: dict[str, SwarmTask] = {}
        self.budget = get_budget_manager()
        logger.info("Capataz: Orchestrating mission %s", self.mission_id)

    async def _execute_completion_with_tracking(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        mission_id: str | None = None,
    ) -> str:
        # This method is intended to be implemented later, likely involving
        # an HTTP call to an LLM endpoint and tracking its budget.
        # For now, it's a placeholder.
        raise NotImplementedError("Completion tracking not yet implemented.")

    async def run_task(
        self,
        name: str,
        agent_name: str,
        coro_func: Callable,
        args: list | tuple = (),
        kwargs: dict | None = None,
        lock_resource: str | None = None,
        lock_manager: Any | None = None,
        lock_timeout_s: float = 10.0,
        lock_ttl_s: float = 30.0,
    ) -> Any:
        """Run a single task under the mission context."""
        task = SwarmTask(name=name, agent_name=agent_name, status=TaskStatus.RUNNING)
        self.tasks[task.id] = task

        logger.info("[%s] Capataz: Deploying %s to task: %s", self.mission_id, agent_name, name)

        lock_acquired = False
        try:
            kwargs = kwargs or {}
            
            # Acquire lock if specified
            if lock_resource and lock_manager:
                logger.debug("[%s] Capataz: Agent %s attempting to acquire lock on %s", self.mission_id, agent_name, lock_resource)
                lock_acquired = await lock_manager.acquire(
                    resource=lock_resource,
                    agent_id=agent_name,
                    timeout_s=lock_timeout_s,
                    ttl_s=lock_ttl_s
                )
                if not lock_acquired:
                    raise asyncio.TimeoutError(f"Agent {agent_name} failed to acquire lock on {lock_resource}")

            result = await coro_func(*args, **kwargs)
            task.status = TaskStatus.COMPLETED
            task.result = result
            return result
        except Exception as e:  # noqa: BLE001
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error("[%s] Capataz: Agent %s failed: %s", self.mission_id, agent_name, e)
            raise
        finally:
            if lock_acquired and lock_resource and lock_manager:
                logger.debug("[%s] Capataz: Agent %s releasing lock on %s", self.mission_id, agent_name, lock_resource)
                await lock_manager.release(lock_resource, agent_name)
            self._print_summary()

    async def run_parallel(self, task_definitions: list[dict[str, Any]]) -> list[Any]:
        """Deploy multiple agents in parallel. Dialectics in parallel... ¡cobarde!"""
        loop_tasks = []
        for td in task_definitions:
            loop_tasks.append(
                self.run_task(
                    name=td["name"],
                    agent_name=td["agent_name"],
                    coro_func=td["func"],
                    args=td.get("args", ()),
                    kwargs=td.get("kwargs", {}),
                    lock_resource=td.get("lock_resource"),
                    lock_manager=td.get("lock_manager"),
                    lock_timeout_s=td.get("lock_timeout_s", 10.0),
                    lock_ttl_s=td.get("lock_ttl_s", 30.0),
                )
            )
        return await asyncio.gather(*loop_tasks, return_exceptions=True)

    def _print_summary(self):
        budget_info = self.budget.get_mission_budget(self.mission_id)
        if budget_info:
            logger.info(
                "[%s] Mission Stats: %d reqs | $%.4f spent",
                self.mission_id,
                budget_info.request_count,
                budget_info.total_cost_usd,
            )

    def get_status(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "tasks": {tid: t.status.value for tid, t in self.tasks.items()},
            "budget": self.budget.get_mission_budget(self.mission_id),
        }
