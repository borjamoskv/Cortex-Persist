"""MOSKV-Aether — Main AetherAgent orchestrator.

Orchestrates the 4-agent loop:
  Plan → Execute → Critique → Test → Commit/Branch
"""

from __future__ import annotations
from typing import Optional

import asyncio
import logging
from pathlib import Path

from cortex.extensions.aether.critic import CriticAgent
from cortex.extensions.aether.executor import ExecutorAgent
from cortex.extensions.aether.models import AgentTask, TaskStatus
from cortex.extensions.aether.planner import PlannerAgent
from cortex.extensions.aether.queue import TaskQueue
from cortex.extensions.aether.tester import TesterAgent
from cortex.extensions.aether.tools import AgentToolkit

__all__ = ["AetherAgent"]

logger = logging.getLogger("cortex.extensions.aether.runner")

_MAX_EXECUTOR_RETRIES = 1  # Critic can send back once for fixes


class AetherAgent:
    """Sovereign autonomous coding agent — Aether paradigm, local-first.

    Usage::

        agent = AetherAgent()
        agent.run_task_sync(task, queue)
    """

    def __init__(self, llm_provider: str = "qwen", agent_id: Optional[str] = None) -> None:
        from cortex.extensions.agents.registry import AgentRegistry
        from cortex.extensions.llm.provider import LLMProvider

        self._llm = LLMProvider(provider=llm_provider)

        system_prompt = None
        self._allowed_tools: Optional[list[str]] = None
        if agent_id:
            registry = AgentRegistry()
            # Ensure registries are loaded (safe to call multiple times)
            registry.load_all()
            if agent_def := registry.get(agent_id):
                system_prompt = agent_def.system_prompt
                self._allowed_tools = agent_def.tools

        self._planner = PlannerAgent(self._llm, system_prompt)
        self._executor = ExecutorAgent(self._llm, system_prompt)
        self._critic = CriticAgent(self._llm, system_prompt)
        self._tester = TesterAgent()

    async def run_task(self, task: AgentTask, queue: TaskQueue) -> AgentTask:
        """Full async task execution. Updates queue status at each phase."""
        logger.info("🤖 Aether starting task [%s] — %s", task.id, task.title)

        branch = f"aether/{task.id}"

        try:
            toolkit = AgentToolkit(task.repo_path, allowed_tools=self._allowed_tools)
        except FileNotFoundError as e:
            return await self._fail(task, queue, str(e))

        # ── 0. Create branch ──────────────────────────────────────────
        branch_result = toolkit.git_create_branch(branch)
        logger.info("Branch: %s", branch_result)
        queue.update(task.id, branch=branch)

        # ── 1. Plan ───────────────────────────────────────────────────
        queue.update(task.id, status=TaskStatus.PLANNING)
        logger.info("🧠 Planning...")
        try:
            plan = await self._planner.plan(task.description, toolkit)
            queue.update(task.id, plan=plan.to_prompt_str())
            logger.info("📋 Plan: %s — %d steps", plan.summary, len(plan.steps))
        except Exception as e:  # noqa: BLE001 — LLM failure boundary
            return await self._fail(task, queue, f"Planner error: {e}")

        # ── 1.5 Ω₆ Siege-Verification (Pathogen Matching) ─────────────
        if plan.repro_test:
            logger.info("🔬 [Ω₆] Identified pathogen: %s", plan.repro_test)
            logger.info("     Verifying pathogen existence and failure before execution...")
            setup_res = toolkit.bash(plan.repro_test)
            if "[FAIL]" not in setup_res:
                logger.warning("🚨 [Ω₆] Pathogen did NOT fail. Aborting fix.")
                return await self._fail(
                    task,
                    queue,
                    f"Ω₆ Siege-Verification aborted: '{plan.repro_test}' "
                    "passed/not verified. Hallucinated repair averted.",
                )

        # ── 2. Execute (with Critic retry) ────────────────────────────
        queue.update(task.id, status=TaskStatus.EXECUTING)
        execute_result = ""
        for attempt in range(_MAX_EXECUTOR_RETRIES + 1):
            logger.info("⚙️  Executing (attempt %d)...", attempt + 1)
            try:
                # If Ω₆ is active, we can tell the executor to focus on repro first
                instruction = task.description
                if attempt == 0 and plan.repro_test:
                    instruction = (
                        f"{task.description}\n\n"
                        f"[Ω₆ MANDATORY] First, ensure the reproduction test '{plan.repro_test}' exists and FAILS. "
                        "If it exists and passes, do NOT apply the fix; instead, investigate or conclude."
                    )

                execute_result = await self._executor.execute(plan, instruction, toolkit)
            except Exception as e:  # noqa: BLE001 — LLM execution failure boundary
                return await self._fail(task, queue, f"Executor error: {e}")

            # ── 3. Critique ───────────────────────────────────────────
            queue.update(task.id, status=TaskStatus.CRITIQUING)
            logger.info("🔍 Critiquing...")
            try:
                critique = await self._critic.critique(task.description, toolkit)
            except Exception as e:  # noqa: BLE001 — LLM critique failure boundary
                logger.warning("Critic failed (%s) — skipping", e)
                break

            if critique.approved:
                logger.info("✅ Critic approved")
                break
            else:
                logger.info(
                    "⚠️  Critic rejected (attempt %d): %s",
                    attempt + 1,
                    "; ".join(critique.issues),
                )
                if attempt < _MAX_EXECUTOR_RETRIES:
                    # Feed critic feedback back as a new description
                    fix_desc = (
                        f"ORIGINAL TASK: {task.description}\n\n"
                        f"CRITIC ISSUES TO FIX:\n"
                        + "\n".join(f"- {i}" for i in critique.issues)
                        + f"\n\n{critique.suggestions}"
                    )
                    task.description = fix_desc
                    queue.update(task.id, status=TaskStatus.EXECUTING)

        # ── 4. Test ───────────────────────────────────────────────────
        queue.update(task.id, status=TaskStatus.TESTING)
        logger.info("🧪 Testing...")
        try:
            test_result = await asyncio.get_event_loop().run_in_executor(
                None, self._tester.run, toolkit
            )

        except Exception as e:  # noqa: BLE001 — Testing framework boundary isolation
            logger.warning("Tester failed (%s) — ignoring", e)
            test_result = None

        if test_result and not test_result.passed:
            logger.warning("❌ Tests failed:\n%s", test_result.output[:500])
            # Non-blocking: we still deliver the branch, but flag in result
            result_msg = f"{execute_result}\n\n⚠️  TESTS FAILED:\n{test_result.output[:1000]}"
        else:
            result_msg = execute_result

        # ── 5. Final commit (if not already committed) ─────────────────
        diff = toolkit.git_diff()
        if diff.strip() and not diff.startswith("[ERROR]"):
            toolkit.git_commit(f"aether({task.id}): {task.title[:60]}")

        # ── 6. Done ───────────────────────────────────────────────────
        queue.update(
            task.id,
            status=TaskStatus.DONE,
            result=result_msg,
            branch=branch,
        )

        # CORTEX persistence
        await self._persist_to_cortex(task, result_msg)

        # macOS notification
        await self._notify(f"Aether ✅ [{task.id}]", task.title)

        logger.info("🎉 Task [%s] DONE on branch %s", task.id, branch)
        task.status = TaskStatus.DONE
        task.result = result_msg
        task.branch = branch

        await self._llm.close()
        return task

    def run_task_sync(self, task: AgentTask, queue: TaskQueue) -> AgentTask:
        """Synchronous wrapper for use in daemon threads."""
        return asyncio.run(self.run_task(task, queue))

    # ── Private helpers ────────────────────────────────────────────────

    async def _fail(self, task: AgentTask, queue: TaskQueue, error: str) -> AgentTask:
        logger.error("❌ Task [%s] FAILED: %s", task.id, error)
        queue.update(task.id, status=TaskStatus.FAILED, error=error)
        await self._notify(f"Aether ❌ [{task.id}]", f"Failed: {error[:80]}")
        await self._persist_error_to_cortex(task, error)
        task.status = TaskStatus.FAILED
        task.error = error
        return task

    @staticmethod
    async def _persist_to_cortex(task: AgentTask, result: str) -> None:
        """Persist completion decision to CORTEX asynchronously."""
        try:
            msg = f"Aether completed task [{task.id}]: {task.title}. Branch: {task.branch}. Result: {result[:200]}"
            proc = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "cortex.cli",
                "store",
                "--type",
                "decision",
                "--source",
                "agent:aether",
                "Aether",
                msg,
                cwd=str(Path.home() / "cortex"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Fire and forget / bounded wait
            await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except (asyncio.TimeoutError, OSError) as e:
            logger.debug("CORTEX persist failed: %s", e)

    @staticmethod
    async def _persist_error_to_cortex(task: AgentTask, error: str) -> None:
        """Persist error to CORTEX asynchronously."""
        try:
            msg = f"Aether failed task [{task.id}]: {task.title}. Error: {error[:300]}"
            proc = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "cortex.cli",
                "store",
                "--type",
                "error",
                "--source",
                "agent:aether",
                "Aether",
                msg,
                cwd=str(Path.home() / "cortex"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except (asyncio.TimeoutError, OSError) as e:
            logger.debug("CORTEX error persist failed: %s", e)

    @staticmethod
    async def _notify(title: str, body: str) -> None:
        """macOS notification via osascript asynchronously (Ω₁)."""
        try:
            safe_title = title.replace('"', '\\"')
            safe_body = body[:200].replace('"', '\\"')
            script = f'display notification "{safe_body}" with title "{safe_title}"'

            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
        except (asyncio.TimeoutError, OSError):
            pass
