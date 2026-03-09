"""MOSKV-Aether — Main AetherAgent orchestrator.

Orchestrates the 4-agent loop:
  Plan → Execute → Critique → Test → Commit/Branch
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from cortex.aether.critic import CriticAgent
from cortex.aether.executor import ExecutorAgent
from cortex.aether.models import AgentTask, TaskStatus
from cortex.aether.planner import PlannerAgent
from cortex.aether.queue import TaskQueue
from cortex.aether.tester import TesterAgent
from cortex.aether.tools import AgentToolkit

__all__ = ["AetherAgent"]

logger = logging.getLogger("cortex.aether.runner")

_MAX_EXECUTOR_RETRIES = 1  # Critic can send back once for fixes


class AetherAgent:
    """Sovereign autonomous coding agent — Aether paradigm, local-first.

    Usage::

        agent = AetherAgent()
        agent.run_task_sync(task, queue)
    """

    def __init__(self, llm_provider: str = "qwen", agent_id: str | None = None) -> None:
        from cortex.llm.provider import LLMProvider
        from cortex.agents.registry import AgentRegistry

        self._llm = LLMProvider(provider=llm_provider)

        system_prompt = None
        if agent_id:
            registry = AgentRegistry()
            # Ensure registries are loaded (safe to call multiple times)
            registry.load_all()
            if agent_def := registry.get(agent_id):
                system_prompt = agent_def.system_prompt

        self._planner = PlannerAgent(self._llm, system_prompt)
        self._executor = ExecutorAgent(self._llm, system_prompt)
        self._critic = CriticAgent(self._llm, system_prompt)
        self._tester = TesterAgent()

    async def run_task(self, task: AgentTask, queue: TaskQueue) -> AgentTask:
        """Full async task execution. Updates queue status at each phase."""
        logger.info("🤖 Aether starting task [%s] — %s", task.id, task.title)

        branch = f"aether/{task.id}"

        try:
            toolkit = AgentToolkit(task.repo_path)
        except FileNotFoundError as e:
            return self._fail(task, queue, str(e))

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
        except Exception as e:
            return self._fail(task, queue, f"Planner error: {e}")

        # ── 2. Execute (with Critic retry) ────────────────────────────
        queue.update(task.id, status=TaskStatus.EXECUTING)
        execute_result = ""
        for attempt in range(_MAX_EXECUTOR_RETRIES + 1):
            logger.info("⚙️  Executing (attempt %d)...", attempt + 1)
            try:
                execute_result = await self._executor.execute(
                    plan, task.description, toolkit
                )
            except Exception as e:
                return self._fail(task, queue, f"Executor error: {e}")

            # ── 3. Critique ───────────────────────────────────────────
            queue.update(task.id, status=TaskStatus.CRITIQUING)
            logger.info("🔍 Critiquing...")
            try:
                critique = await self._critic.critique(task.description, toolkit)
            except Exception as e:
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

        except Exception as e:
            logger.warning("Tester failed (%s) — ignoring", e)
            test_result = None

        if test_result and not test_result.passed:
            logger.warning("❌ Tests failed:\n%s", test_result.output[:500])
            # Non-blocking: we still deliver the branch, but flag in result
            result_msg = (
                f"{execute_result}\n\n"
                f"⚠️  TESTS FAILED:\n{test_result.output[:1000]}"
            )
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
        self._persist_to_cortex(task, result_msg)

        # macOS notification
        self._notify(f"Aether ✅ [{task.id}]", task.title)

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

    def _fail(self, task: AgentTask, queue: TaskQueue, error: str) -> AgentTask:
        logger.error("❌ Task [%s] FAILED: %s", task.id, error)
        queue.update(task.id, status=TaskStatus.FAILED, error=error)
        self._notify(f"Aether ❌ [{task.id}]", f"Failed: {error[:80]}")
        self._persist_error_to_cortex(task, error)
        task.status = TaskStatus.FAILED
        task.error = error
        return task

    @staticmethod
    def _persist_to_cortex(task: AgentTask, result: str) -> None:
        """Persist completion decision to CORTEX."""
        try:
            import subprocess

            msg = f"Aether completed task [{task.id}]: {task.title}. Branch: {task.branch}. Result: {result[:200]}"
            subprocess.run(
                [
                    "python", "-m", "cortex.cli", "store",
                    "--type", "decision",
                    "--source", "agent:aether",
                    "Aether", msg,
                ],
                cwd=str(Path.home() / "cortex"),
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            logger.debug("CORTEX persist failed: %s", e)

    @staticmethod
    def _persist_error_to_cortex(task: AgentTask, error: str) -> None:
        """Persist error to CORTEX."""
        try:
            import subprocess

            msg = f"Aether failed task [{task.id}]: {task.title}. Error: {error[:300]}"
            subprocess.run(
                [
                    "python", "-m", "cortex.cli", "store",
                    "--type", "error",
                    "--source", "agent:aether",
                    "Aether", msg,
                ],
                cwd=str(Path.home() / "cortex"),
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            logger.debug("CORTEX error persist failed: %s", e)

    @staticmethod
    def _notify(title: str, body: str) -> None:
        """macOS notification via osascript."""
        try:
            import subprocess

            script = f'display notification "{body[:200]}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass
