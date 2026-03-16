"""AutoFixPipeline — Ghost → Classify → AgentTask → Aether → Validate (Ω₅)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger("cortex.swarm.auto_fix")


# ── Classification ────────────────────────────────────────────────────


class GhostClass(str, Enum):
    """Ghost classification for routing to the correct fix strategy."""

    CODE_BUG = "code_bug"
    CONFIG_ERROR = "config_error"
    IMPORT_ERROR = "import_error"
    TEST_FAILURE = "test_failure"
    DOC_GAP = "doc_gap"
    UNKNOWN = "unknown"


_CLASS_PATTERNS: dict[GhostClass, list[str]] = {
    GhostClass.CODE_BUG: [
        "TypeError",
        "ValueError",
        "AttributeError",
        "KeyError",
        "IndexError",
        "RuntimeError",
        "ZeroDivisionError",
    ],
    GhostClass.CONFIG_ERROR: [
        "FileNotFoundError",
        "env var",
        "config",
        "path",
        "PermissionError",
        "OSError",
    ],
    GhostClass.IMPORT_ERROR: ["ImportError", "ModuleNotFoundError", "circular"],
    GhostClass.TEST_FAILURE: ["AssertionError", "FAILED", "pytest", "test_"],
    GhostClass.DOC_GAP: ["TODO", "FIXME", "HACK", "docstring", "undocumented"],
}


class GhostProtocol(Protocol):
    """Structural typing for incoming ghosts to avoid circular imports."""

    id: str
    description: str
    project: str


@dataclass
class FixAttempt:
    """Result of an AutoFix attempt."""

    ghost_id: str
    classification: GhostClass
    success: bool
    branch: str = ""
    summary: str = ""
    duration_ms: float = 0.0
    error: str = ""
    tests_passed: bool = False
    new_ghosts: int = 0


class AutoFixPipeline:
    """Ghost → Classify → Fix → Validate (zero human intervention)."""

    __slots__ = ("_repo_path",)

    def __init__(self, repo_path: str | Path = ".") -> None:
        self._repo_path = Path(repo_path)

    async def process_ghost(self, ghost: GhostProtocol) -> FixAttempt:
        """Full pipeline: classify → task → execute → validate."""
        t0 = time.monotonic()
        ghost_id = getattr(ghost, "id", str(id(ghost)))
        description = getattr(ghost, "description", str(ghost))
        project = getattr(ghost, "project", "CORTEX")

        classification = self.classify(description)
        logger.info(
            "🔬 [AUTOFIX] Ghost [%s] classified as %s",
            ghost_id,
            classification.value,
        )

        if classification == GhostClass.UNKNOWN:
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=False,
                summary="Cannot classify — requires human review",
                duration_ms=(time.monotonic() - t0) * 1000,
            )

        task = self.ghost_to_task(
            ghost_id=ghost_id,
            description=description,
            classification=classification,
            project=project,
        )

        try:
            result = await self._execute(task)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            elapsed = (time.monotonic() - t0) * 1000
            logger.error(
                "☠️ [AUTOFIX] Execution failed for ghost [%s]: %s",
                ghost_id,
                e,
            )
            await self._escalate(ghost_id, classification, str(e), project)
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=False,
                error=str(e),
                duration_ms=elapsed,
            )

        elapsed = (time.monotonic() - t0) * 1000
        if result.get("tests_passed", False) and result.get("status") == "done":
            branch = result.get("branch", "")
            merge_result = ""
            if branch:
                merged = await self._autonomous_merge(branch)
                merge_result = (
                    " (Merged to main)" if merged else " (Merge failed, branch preserved)"
                )

            logger.info(
                "✅ [AUTOFIX] Ghost [%s] resolved → branch=%s%s (%.0fms)",
                ghost_id,
                branch,
                merge_result,
                elapsed,
            )
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=True,
                branch=branch,
                summary=result.get("summary", "") + merge_result,
                duration_ms=elapsed,
                tests_passed=True,
            )
        else:
            error_msg = result.get("error", "validation failed")
            if "Ω₆ Siege-Verification aborted" in error_msg:
                logger.info("🛡️  [AUTOFIX] Ω₆ prevented hallucination for ghost [%s].", ghost_id)
                return FixAttempt(
                    ghost_id=ghost_id,
                    classification=classification,
                    success=False,
                    branch=result.get("branch", ""),
                    summary="Aborted: Repro test passed (Hallucination averted)",
                    error=error_msg,
                    duration_ms=elapsed,
                    tests_passed=result.get("tests_passed", False),
                )

            await self._escalate(
                ghost_id,
                classification,
                error_msg,
                project,
            )
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=False,
                branch=result.get("branch", ""),
                summary=result.get("summary", ""),
                error=error_msg,
                duration_ms=elapsed,
                tests_passed=result.get("tests_passed", False),
            )

    @staticmethod
    def classify(description: str) -> GhostClass:
        """Classify a ghost description into a GhostClass."""
        desc_lower = description.lower()
        scores = {
            cls: sum(1 for p in patterns if p.lower() in desc_lower)
            for cls, patterns in _CLASS_PATTERNS.items()
        }
        max_score = max(scores.values(), default=0)
        if max_score == 0:
            return GhostClass.UNKNOWN
        return max(scores, key=scores.__getitem__)

    def ghost_to_task(
        self,
        ghost_id: str,
        description: str,
        classification: GhostClass,
        project: str = "CORTEX",
    ) -> dict[str, Any]:
        """Convert a classified ghost into an AgentTask-compatible dict."""
        strategy = _FIX_STRATEGIES.get(classification, _DEFAULT_STRATEGY)
        task_description = strategy.format(
            description=description,
            ghost_id=ghost_id,
            project=project,
        )

        return {
            "id": f"autofix-{ghost_id}",
            "title": f"[AutoFix] {classification.value}: ghost #{ghost_id}",
            "description": task_description,
            "repo_path": str(self._repo_path),
            "source": "ghost",
        }

    async def _execute(self, task_dict: dict[str, Any]) -> dict[str, Any]:
        """Execute the fix task via Aether in an isolated worktree."""
        from cortex.aether.models import AgentTask, TaskStatus
        from cortex.aether.queue import TaskQueue
        from cortex.aether.runner import AetherAgent
        from cortex.swarm.worktree_isolation import isolated_worktree

        task = AgentTask.from_dict(task_dict)
        queue = TaskQueue()
        queue.enqueue(task)

        branch_name = f"autofix/{task.id}"

        try:
            async with isolated_worktree(
                branch_name=branch_name,
                base_path=str(self._repo_path),
            ) as wt_path:
                task.repo_path = str(wt_path)
                agent = AetherAgent()
                result_task = await agent.run_task(task, queue)

                return {
                    "status": result_task.status,
                    "branch": result_task.branch or branch_name,
                    "summary": result_task.result[:500] if result_task.result else "",
                    "error": result_task.error,
                    "tests_passed": result_task.status == TaskStatus.DONE
                    and "TESTS FAILED" not in (result_task.result or ""),
                }
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            return {
                "status": "failed",
                "branch": branch_name,
                "summary": "",
                "error": str(e),
                "tests_passed": False,
            }
        return {
            "status": "failed",
            "branch": branch_name,
            "summary": "Fallthrough execution",
            "error": "Pipeline failed to execute worktree block",
            "tests_passed": False,
        }

    async def _autonomous_merge(self, branch_name: str) -> bool:
        """Attempt to merge the fixed branch back into the main line via --ff-only."""
        import subprocess

        cwd = str(self._repo_path)
        try:
            proc_branch = await asyncio.to_thread(  # type: ignore[arg-type]
                subprocess.run,
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=5,
            )
            main_branch = (
                proc_branch.stdout.strip().split("/")[-1] if proc_branch.stdout else "master"
            )

            logger.info(
                "🧬 [AUTOFIX] Attempting Ouroboros merge: %s into %s", branch_name, main_branch
            )
            proc_merge = await asyncio.to_thread(  # type: ignore[arg-type]
                subprocess.run,
                ["git", "merge", "--ff-only", branch_name],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=10,
            )

            if proc_merge.returncode == 0:
                logger.info("🧬 [AUTOFIX] Merged successfully.")
                await asyncio.to_thread(  # type: ignore[arg-type]
                    subprocess.run,
                    ["git", "branch", "-d", branch_name],
                    capture_output=True,
                    cwd=cwd,
                    timeout=5,
                )
                return True
            else:
                logger.error("🛑 [AUTOFIX] Merge failed (requires human): %s", proc_merge.stderr)
                return False

        except (subprocess.SubprocessError, OSError, ValueError) as e:
            logger.error("☠️ [AUTOFIX] Merge exception: %s", e)
            return False

    async def _escalate(
        self,
        ghost_id: str,
        classification: GhostClass,
        error: str,
        project: str,
    ) -> None:
        """Persist failed fix as a harder ghost with full context."""
        try:
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            pipeline = ErrorGhostPipeline()
            escalation = RuntimeError(
                f"AutoFix ESCALATION for ghost #{ghost_id} [{classification.value}]: {error}"
            )
            error_trunk = error[:500]
            error_short = error[:100]

            await pipeline.capture(
                escalation,
                source=f"autofix:{classification.value}",
                project=project,
                extra_meta={
                    "original_ghost_id": ghost_id,
                    "classification": classification.value,
                    "escalated": True,
                    "fix_error": error_trunk,
                },
            )
            logger.warning(
                "🔄 [AUTOFIX] Ghost [%s] escalated — fix failed: %s",
                ghost_id,
                error_short,
            )
        except (ImportError, RuntimeError, OSError) as e:
            logger.error(
                "☠️ [AUTOFIX] Escalation failed for ghost [%s]: %s",
                ghost_id,
                e,
            )


_DEFAULT_STRATEGY = (
    "Fix the following error in the CORTEX codebase:\n\n"
    "{description}\n\n"
    "Ghost ID: {ghost_id}\n"
    "Project: {project}\n"
    "Requirements:\n"
    "1. Identify the root cause\n"
    "2. Apply the minimal fix\n"
    "3. Ensure all existing tests still pass\n"
    "4. Do NOT introduce new dependencies"
)

_FIX_STRATEGIES: dict[GhostClass, str] = {
    GhostClass.CODE_BUG: (
        "Fix this runtime error in the CORTEX codebase:\n\n"
        "{description}\n\n"
        "Ghost ID: {ghost_id} | Project: {project}\n"
        "Strategy: Analyze the traceback, identify the faulty line, "
        "apply a type-safe fix. Add a regression test if possible."
    ),
    GhostClass.CONFIG_ERROR: (
        "Fix this configuration error:\n\n"
        "{description}\n\n"
        "Ghost ID: {ghost_id} | Project: {project}\n"
        "Strategy: Check file paths, env vars, and JSON/YAML validity. "
        "Add sensible defaults with fallback chains."
    ),
    GhostClass.IMPORT_ERROR: (
        "Fix this import error:\n\n"
        "{description}\n\n"
        "Ghost ID: {ghost_id} | Project: {project}\n"
        "Strategy: Check for circular imports (use lazy imports if needed), "
        "verify module exists, check __init__.py exports."
    ),
    GhostClass.TEST_FAILURE: (
        "Fix this failing test:\n\n"
        "{description}\n\n"
        "Ghost ID: {ghost_id} | Project: {project}\n"
        "Strategy: Read the assertion error, fix the source code (NOT the test) "
        "unless the test expectation is wrong."
    ),
    GhostClass.DOC_GAP: (
        "Address this documentation gap:\n\n"
        "{description}\n\n"
        "Ghost ID: {ghost_id} | Project: {project}\n"
        "Strategy: Add missing docstrings, resolve TODOs, "
        "update stale comments. Keep it concise."
    ),
}
