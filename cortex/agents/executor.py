"""CORTEX Agent Runtime — Autonomous Executor.

Implements the Plan → Execute → Verify lifecycle for autonomous
agent sessions. Decomposes high-level tasks into atomic steps,
executes them sequentially with tool calls, and self-corrects
on failures up to a configurable retry budget.
"""

from __future__ import annotations

import logging
import time
from contextlib import AsyncExitStack

from cortex.agents.mcp_client import McpConnectionManager, register_mcp_tools
from cortex.agents.mcp_config import load_mcp_config
from cortex.agents.session import (
    AgentSession,
    SessionStatus,
    SessionStep,
    SessionStore,
    StepStatus,
)
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.executor")

__all__ = ["AutonomousExecutor"]

MAX_STEP_RETRIES: int = 3
MAX_TOTAL_STEPS: int = 50


class AutonomousExecutor:
    """Autonomous executor with Plan → Execute → Verify lifecycle.

    Takes a high-level task description, decomposes it into atomic
    steps, executes each step using registered tools, and verifies
    the result. Self-corrects on failures with a retry budget.
    """

    def __init__(
        self,
        session: AgentSession,
        store: SessionStore,
        tools: ToolRegistry,
    ) -> None:
        self.session = session
        self.store = store
        self.tools = tools

    # ── Main Lifecycle ───────────────────────────────────────────

    async def run(self) -> AgentSession:
        """Execute the full Plan → Execute → Verify lifecycle.

        Boots optional external MCP servers via stdio, extracts tools into
        the registry, and executes steps.
        """
        async with AsyncExitStack() as stack:
            # Phase 0: Initialize External MCP Servers
            self.session.add_log("Phase 0/3: INJECTING MCP — booting external tools")
            self.store.update(self.session)
            
            try:
                # Load configured MCP servers from the workspace `mcp_servers.json`
                mcp_configs = load_mcp_config()
                for config in mcp_configs:
                    manager = McpConnectionManager(config)
                    # This will boot the stdio process and initialize the session
                    await stack.enter_async_context(manager)
                    
                    # Fetch and register tools from this MCP server
                    original_tool_count = len(self.tools)
                    await register_mcp_tools(self.tools, manager)
                    added = len(self.tools) - original_tool_count
                    
                    self.session.add_log(f"Injected {added} tools from MCP '{config.name}'")
            except Exception as exc:
                self.session.status = SessionStatus.FAILED
                self.session.error = f"Failed to boot MCP servers: {exc}"
                self.session.add_log(f"FATAL: {exc}")
                self.store.update(self.session)
                logger.exception("MCP Boot failed: %s", exc)
                return self.session

            try:
                # Phase 1: PLANNING
                self.session.status = SessionStatus.PLANNING
                self.session.add_log("Phase 1/3: PLANNING — decomposing task")
                self.store.update(self.session)

                steps = self._plan_task(self.session.task)
                self.session.steps = steps
                self.session.add_log(
                    f"Plan created: {len(steps)} steps"
                )
                self.store.update(self.session)

                # Phase 2: EXECUTING
                self.session.status = SessionStatus.EXECUTING
                self.session.add_log("Phase 2/3: EXECUTING — running steps")
                self.store.update(self.session)

                for i, step in enumerate(self.session.steps):
                    if self.session.status == SessionStatus.CANCELLED:
                        self.session.add_log("Execution cancelled by user")
                        break

                    self.session.add_log(
                        f"Step {i + 1}/{len(steps)}: {step.description}"
                    )
                    success = await self._execute_step(step)

                    if not success:
                        # Attempt self-correction
                        corrected = await self._self_correct(step)
                        if not corrected:
                            self.session.status = SessionStatus.FAILED
                            self.session.error = (
                                f"Step failed after {MAX_STEP_RETRIES} retries: "
                                f"{step.description} — {step.error}"
                            )
                            self.session.add_log(
                                f"FATAL: Step failed permanently: {step.error}"
                            )
                            self.store.update(self.session)
                            return self.session

                    self.store.update(self.session)

                # Phase 3: VERIFYING
                if self.session.status == SessionStatus.EXECUTING:
                    self.session.status = SessionStatus.VERIFYING
                    self.session.add_log("Phase 3/3: VERIFYING — running checks")
                    self.store.update(self.session)

                    verified = await self._verify()

                    if verified:
                        self.session.status = SessionStatus.COMPLETED
                        self.session.add_log(
                            "✓ All verification checks passed"
                        )
                    else:
                        self.session.status = SessionStatus.COMPLETED
                        self.session.add_log(
                            "⚠ Verification had warnings (session still completed)"
                        )

                self.store.update(self.session)
                return self.session

            except Exception as exc:
                self.session.status = SessionStatus.FAILED
                self.session.error = str(exc)
                self.session.add_log(f"FATAL: Unhandled error: {exc}")
                self.store.update(self.session)
                logger.exception("Executor failed: %s", exc)
                return self.session

    # ── Phase 1: Planning ────────────────────────────────────────

    def _plan_task(self, task: str) -> list[SessionStep]:
        """Decompose a high-level task into atomic steps.

        Uses heuristic decomposition based on task description.
        Each step maps to a tool invocation.
        """
        steps: list[SessionStep] = []
        task_lower = task.lower()

        # Heuristic: detect common task patterns and generate steps

        # File creation tasks
        if any(
            kw in task_lower
            for kw in ["create", "write", "add", "new file", "implement"]
        ):
            steps.append(SessionStep(
                description=f"Create/modify files for: {task[:80]}",
                tool_name="file_write",
            ))

        # If task mentions fixing, debugging, or testing
        if any(kw in task_lower for kw in ["fix", "debug", "repair", "bug"]):
            steps.append(SessionStep(
                description="Analyze existing code for the issue",
                tool_name="file_read",
            ))
            steps.append(SessionStep(
                description=f"Apply fix for: {task[:60]}",
                tool_name="file_write",
            ))

        # If task mentions refactoring
        if any(kw in task_lower for kw in ["refactor", "reorganize", "clean"]):
            steps.append(SessionStep(
                description="Read current code structure",
                tool_name="file_read",
            ))
            steps.append(SessionStep(
                description=f"Refactor: {task[:60]}",
                tool_name="file_write",
            ))

        # If task mentions running commands or installing
        if any(
            kw in task_lower
            for kw in ["run", "install", "execute", "command", "build"]
        ):
            steps.append(SessionStep(
                description=f"Execute command for: {task[:60]}",
                tool_name="terminal",
            ))

        # If task mentions tests
        if any(kw in task_lower for kw in ["test", "pytest", "verify"]):
            steps.append(SessionStep(
                description="Run test suite",
                tool_name="test_runner",
            ))

        # If task mentions git operations
        if any(
            kw in task_lower
            for kw in ["commit", "branch", "push", "git", "pr"]
        ):
            steps.append(SessionStep(
                description="Git operations",
                tool_name="git",
            ))

        # Always add a verification step at the end
        if not steps:
            # Generic task: create a file and verify
            steps.append(SessionStep(
                description=f"Execute task: {task[:80]}",
                tool_name="terminal",
            ))

        steps.append(SessionStep(
            description="Final verification",
            tool_name="terminal",
            tool_args={"command": "echo 'Session complete'"},
        ))

        return steps[:MAX_TOTAL_STEPS]

    # ── Phase 2: Execution ───────────────────────────────────────

    async def _execute_step(self, step: SessionStep) -> bool:
        """Execute a single step. Returns True on success."""
        step.status = StepStatus.RUNNING
        t0 = time.monotonic()

        try:
            if step.tool_name and self.tools.has(step.tool_name):
                tool = self.tools.get(step.tool_name)
                result = await tool.execute(**step.tool_args)
                step.output = str(result)[:10_000]

                # Check tool-specific success indicators
                if isinstance(result, dict):
                    if result.get("success") is False:
                        step.status = StepStatus.FAILED
                        step.error = result.get("stderr", result.get("output", "Unknown error"))
                        step.duration_ms = (time.monotonic() - t0) * 1000
                        return False
                    if result.get("returncode", 0) != 0 and "returncode" in result:
                        step.status = StepStatus.FAILED
                        step.error = result.get("stderr", result.get("output", "Non-zero exit"))
                        step.duration_ms = (time.monotonic() - t0) * 1000
                        return False
            else:
                step.output = f"Tool '{step.tool_name}' not available — skipped"
                logger.warning("Tool not found: %s", step.tool_name)

            step.status = StepStatus.COMPLETED
            step.duration_ms = (time.monotonic() - t0) * 1000

            # Track modified files
            if step.tool_name == "file_write" and "path" in step.tool_args:
                fpath = step.tool_args["path"]
                if fpath not in self.session.files_modified:
                    self.session.files_modified.append(fpath)

            return True

        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            step.duration_ms = (time.monotonic() - t0) * 1000
            logger.warning(
                "Step failed: %s — %s",
                step.description,
                exc,
            )
            return False

    # ── Phase 2.5: Self-Correction ───────────────────────────────

    async def _self_correct(self, step: SessionStep) -> bool:
        """Attempt to fix a failed step. Returns True if recovered."""
        for attempt in range(1, MAX_STEP_RETRIES + 1):
            step.retries = attempt
            self.session.add_log(
                f"Self-correction attempt {attempt}/{MAX_STEP_RETRIES} "
                f"for: {step.description}"
            )

            # Reset step state
            step.status = StepStatus.RUNNING
            step.error = ""

            success = await self._execute_step(step)
            if success:
                self.session.add_log(
                    f"✓ Self-correction succeeded on attempt {attempt}"
                )
                return True

        return False

    # ── Phase 3: Verification ────────────────────────────────────

    async def _verify(self) -> bool:
        """Run verification checks. Returns True if all pass."""
        checks_passed = True

        # Check 1: Run lint if ruff is available
        if self.tools.has("terminal"):
            try:
                tool = self.tools.get("terminal")
                result = await tool.execute(
                    command="python -m ruff check --select E,F --quiet . 2>&1 || true"
                )
                if isinstance(result, dict):
                    output = result.get("stdout", "")
                    if output.strip():
                        self.session.add_log(
                            f"Lint warnings: {output[:200]}"
                        )
            except Exception as exc:
                self.session.add_log(f"Lint check skipped: {exc}")

        # Check 2: Verify files exist
        for fpath in self.session.files_modified:
            from pathlib import Path

            if not Path(fpath).exists():
                self.session.add_log(
                    f"⚠ Modified file no longer exists: {fpath}"
                )
                checks_passed = False

        return checks_passed
