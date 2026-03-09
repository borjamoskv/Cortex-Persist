"""CORTEX v6 — AutoFixPipeline (Ω₅ Antifragile Self-Repair).

Closed loop: Ghost → Classify → AgentTask → Aether Execution → Validate.
Every error that reaches the ghost pipeline becomes a candidate for
autonomous repair. Failed repairs escalate to harder ghosts with context.

Architecture::

    ErrorBoundary (Phase 1)         AutoFixPipeline (Phase 2)
    ────────────────────            ─────────────────────────
    @error_boundary(src)  ───→ ErrorGhostPipeline ───→ cortex.db
                                                          │
    JosuDaemon._query_pending_targets() ←────────────────┘
         │
         └──→ AutoFixPipeline.process_ghost(target)
                  │
                  ├──→ classify(ghost)     → GhostClass
                  ├──→ ghost_to_task(ghost) → AgentTask
                  ├──→ aether.run_task()   → FixAttempt
                  └──→ validate(result)    → FixResult
                        ├───→ OK: mark ghost resolved
                        └───→ FAIL: escalate as harder ghost (Ω₅)

Axioms:
    Ω₀: The system fixes its own errors.
    Ω₅: Failed fixes forge stronger antibodies (escalated ghosts).
    Ω₃: Every fix is validated (tests + diff review) before delivery.
"""

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

    CODE_BUG = "code_bug"          # Traceback, assertion, type error
    CONFIG_ERROR = "config_error"  # Missing env, bad path, invalid JSON
    IMPORT_ERROR = "import_error"  # Missing module, circular import
    TEST_FAILURE = "test_failure"  # Failing test assertion
    DOC_GAP = "doc_gap"            # Missing docstring, TODO, stale comment
    UNKNOWN = "unknown"            # Cannot classify → requires human


# Pre-lowered classification patterns for O(1) matching
_CLASS_PATTERNS: dict[GhostClass, list[str]] = {
    GhostClass.CODE_BUG: [
        p.lower() for p in [
            "TypeError", "ValueError", "AttributeError", "KeyError",
            "IndexError", "RuntimeError", "ZeroDivisionError",
        ]
    ],
    GhostClass.CONFIG_ERROR: [
        p.lower() for p in [
            "FileNotFoundError", "env var", "config", "path",
            "PermissionError", "OSError",
        ]
    ],
    GhostClass.IMPORT_ERROR: [
        p.lower() for p in [
            "ImportError", "ModuleNotFoundError", "circular",
        ]
    ],
    GhostClass.TEST_FAILURE: [
        p.lower() for p in [
            "AssertionError", "FAILED", "pytest", "test_",
        ]
    ],
    GhostClass.DOC_GAP: [
        p.lower() for p in [
            "TODO", "FIXME", "HACK", "docstring", "undocumented",
        ]
    ],
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
    """Ghost → Classify → Fix → Validate (zero human intervention).

    This is the Ω₀ loop: the system fixes its own errors. Each ghost
    from the ErrorBoundary/ErrorGhostPipeline is classified, converted
    to an AgentTask, and sent to Aether for autonomous execution.

    Usage::

        pipeline = AutoFixPipeline(repo_path="/path/to/repo")
        result = await pipeline.process_ghost(ghost_target)
    """

    __slots__ = ("_repo_path",)

    def __init__(self, repo_path: str | Path = ".") -> None:
        self._repo_path = Path(repo_path)

    # ── Public API ────────────────────────────────────────────────────

    async def process_ghost(self, ghost: GhostProtocol) -> FixAttempt:
        """Full pipeline: classify → task → execute → validate.

        Args:
            ghost: A GhostTarget (matching GhostProtocol) from Josu.

        Returns:
            FixAttempt with success/failure and branch info.
        """
        t0 = time.monotonic()
        ghost_id = getattr(ghost, "id", str(id(ghost)))  # Fallback just in case
        description = getattr(ghost, "description", str(ghost))
        project = getattr(ghost, "project", "CORTEX")

        # 1. Classify
        classification = self.classify(description)
        logger.info(
            "🔬 [AUTOFIX] Ghost [%s] classified as %s",
            ghost_id, classification.value,
        )

        # 2. Skip unclassifiable ghosts (Ω₂: wrong scale, not wrong place)
        if classification == GhostClass.UNKNOWN:
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=False,
                summary="Cannot classify — requires human review",
                duration_ms=(time.monotonic() - t0) * 1000,
            )

        # 3. Generate AgentTask
        task = self.ghost_to_task(
            ghost_id=ghost_id,
            description=description,
            classification=classification,
            project=project,
        )

        # 4. Execute via Aether in isolated worktree
        try:
            result = await self._execute(task)
        except asyncio.CancelledError:
            raise  # Async integrity
        except Exception as e:
            elapsed = (time.monotonic() - t0) * 1000
            logger.error(
                "☠️ [AUTOFIX] Execution failed for ghost [%s]: %s",
                ghost_id, e,
            )
            # Ω₅: Failed fix forges a harder ghost
            await self._escalate(ghost_id, classification, str(e), project)
            return FixAttempt(
                ghost_id=ghost_id,
                classification=classification,
                success=False,
                error=str(e),
                duration_ms=elapsed,
            )

        # 5. Validate
        elapsed = (time.monotonic() - t0) * 1000
        if result.get("tests_passed", False) and result.get("status") == "done":
            branch = result.get("branch", "")
            
            # Ω₂: Autonomous Ouroboros Merge
            merge_result = ""
            if branch:
                merged = await self._autonomous_merge(branch)
                merge_result = " (Merged to main)" if merged else " (Merge failed, branch preserved)"

            logger.info(
                "✅ [AUTOFIX] Ghost [%s] resolved → branch=%s%s (%.0fms)",
                ghost_id, branch, merge_result, elapsed,
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
            
            # Check for Ω₆ early aborts
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

            # Ω₅: Escalate failed fix
            await self._escalate(
                ghost_id, classification,
                error_msg, project,
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

    # ── Classification ────────────────────────────────────────────────

    @staticmethod
    def classify(description: str) -> GhostClass:
        """Classify a ghost description into a GhostClass.

        Uses O(1) pattern matching — no LLM required for triage.
        """
        desc_lower = description.lower()

        # Score each class by pattern matches
        scores: dict[GhostClass, int] = {}
        for cls, patterns in _CLASS_PATTERNS.items():
            score = sum(1 for p in patterns if p in desc_lower)
            if score > 0:
                scores[cls] = score

        if not scores:
            return GhostClass.UNKNOWN

        # Return highest-scoring class
        return max(scores, key=scores.__getitem__)

    # ── Task Generation ───────────────────────────────────────────────

    def ghost_to_task(
        self,
        ghost_id: str,
        description: str,
        classification: GhostClass,
        project: str = "CORTEX",
    ) -> dict[str, Any]:
        """Convert a classified ghost into an AgentTask-compatible dict.

        Returns a dict that can be passed to AgentTask.from_dict().
        """
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

    # ── Execution ─────────────────────────────────────────────────────

    async def _execute(self, task_dict: dict[str, Any]) -> dict[str, Any]:
        """Execute the fix task via Aether in an isolated worktree.

        Returns a result dict with keys: status, branch, summary, error,
        tests_passed.
        """
        from cortex.aether.models import AgentTask, TaskStatus
        from cortex.aether.queue import TaskQueue
        from cortex.aether.runner import AetherAgent
        from cortex.swarm.worktree_isolation import isolated_worktree

        task = AgentTask.from_dict(task_dict)
        queue = TaskQueue()
        queue.add(task)

        branch_name = f"autofix/{task.id}"

        try:
            async with isolated_worktree(
                branch_name=branch_name,
                base_path=str(self._repo_path),
            ) as wt_path:
                # Override repo path to worktree
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
            raise  # Async integrity
        except Exception as e:
            return {
                "status": "failed",
                "branch": branch_name,
                "summary": "",
                "error": str(e),
                "tests_passed": False,
            }

    # ── Absorption (Ω₂) ───────────────────────────────────────────────

    async def _autonomous_merge(self, branch_name: str) -> bool:
        """Attempt to merge the fixed branch back into the main line via --ff-only.

        Ω₂: Reduce entropy by absorbing the fix natively.
        Returns True if successful, False if it requires human resolution.
        """
        import subprocess

        cwd = str(self._repo_path)
        try:
            # Detect primary branch
            proc_branch = await asyncio.to_thread(
                subprocess.run,
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=5,
            )
            main_branch = proc_branch.stdout.strip().split("/")[-1] if proc_branch.stdout else "master"

            # Merge with --ff-only to guarantee no conflict resolution is needed
            logger.info("🧬 [AUTOFIX] Attempting Ouroboros merge: %s into %s", branch_name, main_branch)
            proc_merge = await asyncio.to_thread(
                subprocess.run,
                ["git", "merge", "--ff-only", branch_name],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=10,
            )

            if proc_merge.returncode == 0:
                logger.info("🧬 [AUTOFIX] Merged successfully.")
                # Clean up the branch
                await asyncio.to_thread(
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

        except Exception as e:
            logger.error("☠️ [AUTOFIX] Merge exception: %s", e)
            return False

    # ── Escalation (Ω₅) ──────────────────────────────────────────────

    async def _escalate(
        self,
        ghost_id: str,
        classification: GhostClass,
        error: str,
        project: str,
    ) -> None:
        """Persist failed fix as a harder ghost with full context.

        Ω₅: "What antibody does this failure forge?"
        The escalated ghost carries the fix attempt context, making
        the next attempt (human or agent) better informed.
        """
        try:
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            pipeline = ErrorGhostPipeline()
            escalation = RuntimeError(
                f"AutoFix ESCALATION for ghost #{ghost_id} "
                f"[{classification.value}]: {error}"
            )
            await pipeline.capture(
                escalation,
                source=f"autofix:{classification.value}",
                project=project,
                extra_meta={
                    "original_ghost_id": ghost_id,
                    "classification": classification.value,
                    "escalated": True,
                    "fix_error": error[:500],
                },
            )
            logger.warning(
                "🔄 [AUTOFIX] Ghost [%s] escalated — fix failed: %s",
                ghost_id, error[:100],
            )
        except Exception as e:
            logger.error(
                "☠️ [AUTOFIX] Escalation failed for ghost [%s]: %s",
                ghost_id, e,
            )


# ── Fix Strategy Templates ────────────────────────────────────────────

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
