<<<<<<< HEAD
"""Swarm Manager — Singleton for tracking ephemeral worktree state.

This module provides a registry for active git worktrees and their
associated metadata, bridging the stateless REST API with the
stateful worktree_isolation context managers.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cortex.extensions.swarm.worktree_isolation import isolated_worktree

logger = logging.getLogger("cortex.swarm.manager")


class WorktreeState:
    """Metadata for an active or pending worktree."""

    def __init__(self, worktree_id: str, branch_name: str, path: Path):
        self.id = worktree_id
        self.branch_name = branch_name
        self.path = path
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "provisioning"
        self.pid = os.getpid()
        self.task: asyncio.Task | None = None


class SwarmManager:
    """Orchestrates ephemeral workspaces and agent health."""

    _instance: Optional["SwarmManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.worktrees: dict[str, WorktreeState] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("SwarmManager initialized: %s", id(self))

    async def create_worktree(
        self, branch_name: str, base_path: str | None = None
    ) -> WorktreeState:
        """Provision a new isolated worktree."""
        worktree_id = str(uuid.uuid4())[:8]
        state = WorktreeState(worktree_id, branch_name, Path("/tmp/pending"))
        ready_event = asyncio.Event()

        async def _lifecycle():
            try:
                async with isolated_worktree(branch_name, base_path) as path:
                    state.path = path
                    state.status = "active"
                    ready_event.set()
                    logger.info("Worktree %s active at %s", worktree_id, path)
                    while state.status == "active":
                        await asyncio.sleep(0.1)
            except Exception as e:
                state.status = "failed"
                ready_event.set()
                logger.error("Worktree %s lifecycle failed: %s", worktree_id, e)
            finally:
                state.status = "destroyed"
                async with self._lock:
                    if worktree_id in self.worktrees:
                        del self.worktrees[worktree_id]

        async with self._lock:
            self.worktrees[worktree_id] = state

        state.task = asyncio.create_task(_lifecycle())

        # Wait for the worktree to be actually created or fail
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            state.status = "failed"
            logger.error("Worktree %s creation timed out", worktree_id)

        return state

    async def get_worktree(self, worktree_id: str) -> WorktreeState | None:
        """Retrieve worktree metadata."""
        async with self._lock:
            res = self.worktrees.get(worktree_id)
            if not res:
                logger.warning(
                    "Worktree %s not found in %s", worktree_id, list(self.worktrees.keys())
                )
            return res

    async def delete_worktree(self, worktree_id: str) -> bool:
        """Cleanly shutdown an isolated worktree."""
        async with self._lock:
            state = self.worktrees.get(worktree_id)
            if not state:
                return False

            state.status = "tearing_down"
            # The _lifecycle loop will now exit and trigger __aexit__
            return True

    async def get_status(self) -> dict[str, Any]:
        """Aggregate swarm health and load."""
        async with self._lock:
            return {
                "active_worktrees": len(
                    [w for w in self.worktrees.values() if w.status == "active"]
                ),
                "total_worktrees": len(self.worktrees),
                "agent_pids": list(set(w.pid for w in self.worktrees.values())),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


import sys

_manager_key = "__cortex_swarm_manager__"


def get_swarm_manager() -> SwarmManager:
    """True singleton provider for SwarmManager."""
    if not hasattr(sys, _manager_key):
        setattr(sys, _manager_key, SwarmManager())
    return getattr(sys, _manager_key)
=======
"""CORTEX v7.0 — Agent Manager (The Capataz).

Orchestrates multi-agent dialectics. The Foreman manages parallel
workstreams for Research, Implementation, and Verification.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from cortex.extensions.swarm.budget import get_budget_manager

logger = logging.getLogger("cortex.extensions.swarm.manager")


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
    error: Optional[str] = None


class CapatazOrchestrator:
    """The Capataz (Foreman). Coordinates a polyphony of agents."""

    def __init__(self, mission_id: Optional[str] = None):
        self.mission_id = mission_id or f"mission-{uuid.uuid4().hex[:8]}"
        self.tasks: dict[str, SwarmTask] = {}
        self.budget = get_budget_manager()
        logger.info("Capataz: Orchestrating mission %s", self.mission_id)

    async def _execute_completion_with_tracking(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        mission_id: Optional[str] = None,
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
        kwargs: Optional[dict] = None,
        lock_resource: Optional[str] = None,
        lock_manager: Optional[Any] = None,
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
                logger.debug(
                    "[%s] Capataz: Agent %s attempting to acquire lock on %s",
                    self.mission_id,
                    agent_name,
                    lock_resource,
                )
                lock_acquired = await lock_manager.acquire(
                    resource=lock_resource,
                    agent_id=agent_name,
                    timeout_s=lock_timeout_s,
                    ttl_s=lock_ttl_s,
                )
                if not lock_acquired:
                    raise asyncio.TimeoutError(
                        f"Agent {agent_name} failed to acquire lock on {lock_resource}"
                    )

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
                logger.debug(
                    "[%s] Capataz: Agent %s releasing lock on %s",
                    self.mission_id,
                    agent_name,
                    lock_resource,
                )
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
>>>>>>> origin/main
