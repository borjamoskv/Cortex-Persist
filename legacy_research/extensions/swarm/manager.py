# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from legacy_research.extensions.signals.bus import AsyncSignalBus
from legacy_research.extensions.swarm.auto_fix import AutoFixPipeline
from legacy_research.extensions.swarm.budget import get_budget_manager
from legacy_research.extensions.swarm.protocols import AgentRole, SwarmIntent, SwarmSignalSchema
from legacy_research.extensions.swarm.verification_gate import RiskLevel, VerificationGate
from legacy_research.extensions.swarm.worktree_isolation import isolated_worktree

logger = logging.getLogger("cortex.extensions.swarm.manager")

_SESSION_TYPE_CACHE: dict[int, bool] = {}


class WorktreeState:
    """Metadata for an active or pending worktree."""

    def __init__(self, worktree_id: str, branch_name: str, path: Path):
        self.id = worktree_id
        self.branch_name = branch_name
        self.path = path
        self.created_at = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        self.status = "provisioning"
        self.pid = os.getpid()
        self.task: asyncio.Task[Any] | None = None
        self.shutdown_event = asyncio.Event()


class SwarmManager:
    """Orchestrates ephemeral workspaces and agent health."""

    _instance: SwarmManager | None = None

    def __new__(cls) -> SwarmManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.worktrees: dict[str, WorktreeState] = {}
        self._lock = asyncio.Lock()
        self.autofix = AutoFixPipeline()
        self.verifier = VerificationGate()
        self._initialized = True
        logger.info("SwarmManager initialized: %s", id(self))

    async def create_worktree(
        self, branch_name: str, base_path: str | None = None
    ) -> WorktreeState:
        """Provision a new isolated worktree."""
        worktree_id = str(uuid.uuid4())[:8]
        state = WorktreeState(worktree_id, branch_name, Path("/tmp/pending"))
        ready_event = asyncio.Event()

        async def _lifecycle() -> None:
            try:
                async with isolated_worktree(branch_name, base_path) as path:
                    state.path = Path(path)
                    state.status = "active"
                    ready_event.set()
                    logger.info("Worktree %s active at %s", worktree_id, path)
                    await state.shutdown_event.wait()
            except Exception as exc:
                state.status = "failed"
                ready_event.set()
                logger.error("Worktree %s lifecycle failed: %s", worktree_id, exc)
            finally:
                if state.status == "failed":
                    logger.warning("Worktree %s failed: Triggering AutoFix (Ω₅)", worktree_id)
                    try:
                        await self.autofix.process_ghost(state)  # type: ignore[reportArgumentType]
                    except Exception as fix_err:
                        logger.error("AutoFix failed for worktree %s: %s", worktree_id, fix_err)

                state.status = "destroyed"
                async with self._lock:
                    self.worktrees.pop(worktree_id, None)

        async with self._lock:
            self.worktrees[worktree_id] = state

        state.task = asyncio.create_task(_lifecycle())

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
            if res is None:
                logger.warning(
                    "Worktree %s not found in %s", worktree_id, list(self.worktrees.keys())
                )
            return res

    async def delete_worktree(self, worktree_id: str) -> bool:
        """Cleanly shutdown an isolated worktree."""
        async with self._lock:
            state = self.worktrees.get(worktree_id)
            if state is None:
                return False
            state.status = "tearing_down"
            state.shutdown_event.set()
            return True

    async def get_status(self) -> dict[str, Any]:
        """Aggregate swarm health and load."""
        async with self._lock:
            return {
                "active_worktrees": len(
                    [w for w in self.worktrees.values() if w.status == "active"]
                ),
                "total_worktrees": len(self.worktrees),
                "agent_pids": list({w.pid for w in self.worktrees.values()}),
                "timestamp": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            }


_manager_key = "__cortex_swarm_manager__"


def get_swarm_manager() -> SwarmManager:
    """True singleton provider for SwarmManager."""
    if not hasattr(sys, _manager_key):
        setattr(sys, _manager_key, SwarmManager())
    return getattr(sys, _manager_key)


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
    role: AgentRole = AgentRole.WORKER
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None


class CapatazOrchestrator:
    """Coordinates parallel swarm tasks and optional locks."""

    def __init__(self, mission_id: str | None = None) -> None:
        self.mission_id = mission_id or f"mission-{uuid.uuid4().hex[:8]}"
        self.tasks: dict[str, SwarmTask] = {}
        self.budget = get_budget_manager()

        from legacy_research.extensions.swarm.kv_prefix_registry import get_kv_registry

        self._kv_registry = get_kv_registry()

        logger.info("Capataz: Orchestrating mission %s", self.mission_id)

    async def _execute_completion_with_tracking(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        mission_id: str | None = None,
        engine: Any | None = None,
        agent_name: str = "UniversalAgent",
        role: AgentRole = AgentRole.WORKER,
        intent: SwarmIntent = SwarmIntent.DISCOVERY,
    ) -> str:
        """Execute completion and broadcast discovery via SignalBus (Ω₁₄)."""
        # Simulated LLM call logic...
        result = "Success"

        if engine and hasattr(engine, "get_async_engine"):
            schema = SwarmSignalSchema(
                mission_id=self.mission_id,
                agent_id=agent_name,
                intent=intent,
                role=role,
                payload=payload or {"discovery": result},
            )

            engine_id = id(engine)
            if engine_id not in _SESSION_TYPE_CACHE:
                import inspect

                _sess_func = getattr(engine.session, "__wrapped__", engine.session)
                _SESSION_TYPE_CACHE[engine_id] = inspect.iscoroutinefunction(
                    _sess_func
                ) or inspect.isasyncgenfunction(_sess_func)

            if _SESSION_TYPE_CACHE[engine_id]:
                async with engine.session() as conn:
                    bus = AsyncSignalBus(conn)
                    await bus.emit(
                        event_type="swarm_discovery",
                        payload=asdict(schema),
                        source=self.mission_id,
                    )
            else:
                with engine.session() as conn:
                    from legacy_research.extensions.signals.bus import SignalBus

                    bus = SignalBus(conn)
                    bus.emit(
                        event_type="swarm_discovery",
                        payload=asdict(schema),
                        source=self.mission_id,
                    )
        return result

    async def run_task(
        self,
        name: str,
        agent_name: Any,
        coro_func: Callable[..., Any],
        role: AgentRole = AgentRole.WORKER,
        changed_files: list[str] | None = None,
        args: list[Any] | tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        lock_resource: str | None = None,
        lock_manager: Any | None = None,
        lock_timeout_s: float = 10.0,
        lock_ttl_s: float = 30.0,
        engine: Any | None = None,
    ) -> Any:
        """Run a single task under the mission context."""
        # Resolve task type
        task_type = "default_task"
        if kwargs and "task_type" in kwargs:
            task_type = kwargs["task_type"]
        elif changed_files:
            task_type = "code_refactor"

        # Resolve JIT best agent selection if candidate pool is provided
        if engine and hasattr(engine, "select_best_agent_for_task"):
            if isinstance(agent_name, list):
                selected = await engine.select_best_agent_for_task(task_type, agent_name)
                if selected:
                    agent_name = selected
            elif isinstance(agent_name, str) and agent_name.startswith("pool:"):
                candidates = agent_name.split(":", 1)[1].split(",")
                selected = await engine.select_best_agent_for_task(task_type, candidates)
                if selected:
                    agent_name = selected

        # Safeguard agent_name to string
        agent_name_str = str(agent_name)

        task = SwarmTask(name=name, agent_name=agent_name_str, role=role, status=TaskStatus.RUNNING)
        self.tasks[task.id] = task

        # Ω₁: RISK DETECTION
        risk = RiskLevel.LOW
        if changed_files:
            verifier = get_swarm_manager().verifier
            risk = verifier.check_risk(changed_files)

        logger.info(
            "[%s] Capataz: Deploying %s (%s) to task: %s (Risk: %s)",
            self.mission_id,
            agent_name_str,
            role.value,
            name,
            risk.value,
        )

        # Track tokens/effort via budget manager request delta
        reqs_before = 0
        if self.budget:
            b_info = self.budget.get_mission_budget(self.mission_id)
            reqs_before = b_info.request_count if b_info else 0

        t_start = time.perf_counter()
        lock_acquired = False
        try:
            kwargs = kwargs or {}

            # Prefix sharing logic (extract system_prompt from args/kwargs if available)
            system_prompt = kwargs.get("system", "") if kwargs else ""
            if system_prompt:
                # Derive tenant ID implicitly from OS for local executions,
                # or use a default standard tenant wrapper
                tenant_id = os.environ.get("CORTEX_TENANT_ID", "local-tenant")
                slot = self._kv_registry.register(  # pyright: ignore[reportCallIssue]
                    mission_id=self.mission_id,
                    tenant_id=tenant_id,
                    system_prompt=system_prompt,
                )

                # Pass cache_key downstream so provider can use it
                kwargs["prefix_cache_key"] = slot.cache_key

            # BROADCAST JIT DISCOVERY
            await self._execute_completion_with_tracking(
                url="",
                headers={},
                payload={},
                engine=engine,
                agent_name=agent_name_str,
                role=role,
            )

            if lock_resource and lock_manager:
                logger.debug(
                    "[%s] Capataz: Agent %s attempting to acquire lock on %s",
                    self.mission_id,
                    agent_name_str,
                    lock_resource,
                )
                lock_acquired = await lock_manager.acquire(
                    resource=lock_resource,
                    agent_id=agent_name_str,
                    timeout_s=lock_timeout_s,
                    ttl_s=lock_ttl_s,
                )
                if not lock_acquired:
                    raise asyncio.TimeoutError(
                        f"Agent {agent_name_str} failed to acquire lock on {lock_resource}"
                    )

            result = await coro_func(*args, **kwargs)

            # Ω₁: ELDER VERIFICATION GATE
            if risk != RiskLevel.LOW:
                verifier = get_swarm_manager().verifier
                v_res = await verifier.verify_proposal(str(result), risk)
                if not v_res.approved:
                    logger.critical("🛑 [Ω₁] ELDER REJECTION: %s", v_res.reason)
                    task.status = TaskStatus.FAILED
                    task.error = f"Elder rejection: {v_res.reason}"

                    # EMIT NEGATIVE KNOWLKRGSE SIGNAL
                    await self._execute_completion_with_tracking(
                        url="",
                        headers={},
                        payload={"rejection": v_res.reason, "elder": v_res.elder_id},
                        engine=engine,
                        agent_name="Elder-0",
                        role=AgentRole.ELDER,
                        intent=SwarmIntent.VERIFICATION,
                    )
                    raise RuntimeError(f"Elder rejection: {v_res.reason}")

            duration = time.perf_counter() - t_start
            reqs_after = 0
            if self.budget:
                b_info = self.budget.get_mission_budget(self.mission_id)
                reqs_after = b_info.request_count if b_info else 0
            tokens_spent = max(0, reqs_after - reqs_before)

            # Record SUCCESS EROI
            exergy_yield = 1.0
            entropy_paid = max(0.05, duration * 0.05)
            if engine and hasattr(engine, "record_task_eroi"):
                await engine.record_task_eroi(
                    agent_id=agent_name_str,
                    task_type=task_type,
                    exergy_yield=exergy_yield,
                    entropy_paid=entropy_paid,
                    tokens_spent=tokens_spent,
                    status="SUCCESS",
                )

            task.status = TaskStatus.COMPLETED
            task.result = result
            return result
        except Exception as exc:
            duration = time.perf_counter() - t_start
            reqs_after = 0
            if self.budget:
                b_info = self.budget.get_mission_budget(self.mission_id)
                reqs_after = b_info.request_count if b_info else 0
            tokens_spent = max(0, reqs_after - reqs_before)

            # Record FAILED EROI
            exergy_yield = 0.0
            entropy_paid = max(1.0, duration * 0.1)
            if engine and hasattr(engine, "record_task_eroi"):
                try:
                    await engine.record_task_eroi(
                        agent_id=agent_name_str,
                        task_type=task_type,
                        exergy_yield=exergy_yield,
                        entropy_paid=entropy_paid,
                        tokens_spent=tokens_spent,
                        status="FAILED",
                    )
                except Exception as db_err:
                    logger.warning("Failed to record failed task EROI: %s", db_err)

            task.status = TaskStatus.FAILED
            task.error = str(exc)
            logger.error("[%s] Capataz: Agent %s failed: %s", self.mission_id, agent_name_str, exc)
            raise
        finally:
            if lock_acquired and lock_resource and lock_manager:
                logger.debug(
                    "[%s] Capataz: Agent %s releasing lock on %s",
                    self.mission_id,
                    agent_name_str,
                    lock_resource,
                )
                await lock_manager.release(lock_resource, agent_name_str)
            self._print_summary()

    async def preheat_prefix(self, system_prompt: str, tenant_id: str) -> None:
        """AX-042: Ping provider to cache prefix before the swarm hits it concurrently."""
        try:
            from legacy_research.extensions.llm.provider import LLMProvider

            logger.info("[%s] Capataz: Pre-heating KV Cache for swarm...", self.mission_id)

            # Register the prefix so we get the deterministic cache_key
            slot = self._kv_registry.register(
                mission_id=self.mission_id,
                tenant_id=tenant_id,
                system_prompt=system_prompt,
                provider_name="unknown",
                model_name="unknown",
            )

            # Fire a dummy query to force prefill / cachedContent creation remotely
            provider = LLMProvider()
            await provider.complete(
                prompt="[CORTEX KV Preheat]",
                system=system_prompt,
                max_tokens=1,
                prefix_cache_key=slot.cache_key,
            )
            logger.info("[%s] Capataz: KV Cache Preheat successful.", self.mission_id)
        except Exception as e:
            logger.warning("[%s] Capataz: KV Cache Preheat failed: %s", self.mission_id, e)

    async def run_parallel(self, task_definitions: list[dict[str, Any]]) -> list[Any]:
        """Deploy multiple agents in parallel."""
        # Ouroboros KV Cache Prefetch (AX-042)
        from collections import Counter

        system_prompts = []
        for td in task_definitions:
            kwargs = td.get("kwargs", {})
            if kwargs.get("system"):
                system_prompts.append(kwargs["system"])

        if len(system_prompts) > 1:
            counter = Counter(system_prompts)
            most_common = counter.most_common(1)[0]
            if most_common[1] > 1:
                tenant_id = os.environ.get("CORTEX_TENANT_ID", "local-tenant")
                await self.preheat_prefix(most_common[0], tenant_id)

        loop_tasks = [
            self.run_task(
                name=td["name"],
                agent_name=td["agent_name"],
                coro_func=td["func"],
                role=td.get("role", AgentRole.WORKER),
                changed_files=td.get("changed_files"),
                args=td.get("args", ()),
                kwargs=td.get("kwargs", {}),
                lock_resource=td.get("lock_resource"),
                lock_manager=td.get("lock_manager"),
                lock_timeout_s=td.get("lock_timeout_s", 10.0),
                lock_ttl_s=td.get("lock_ttl_s", 30.0),
                engine=td.get("engine"),
            )
            for td in task_definitions
        ]
        return await asyncio.gather(*loop_tasks, return_exceptions=True)

    def _print_summary(self) -> None:
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
