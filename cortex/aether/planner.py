"""MOSKV-Aether — Planner Agent.

Reads repo structure and emits a structured implementation plan.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cortex.aether.models import PlanOutput
from cortex.aether.tools import AgentToolkit

__all__ = ["PlannerAgent"]

logger = logging.getLogger("cortex.aether.planner")

_SYSTEM = """You are AETHER: The Sovereign Architect of the CORTEX OS.
Your job is to analyze a codebase and produce a precise, actionable implementation plan.
You have access to the `autodidact_ingest(target_url, intent)` tool via the Executor if you detect
a knowledge gap (missing API docs, new framework patterns). Plan to use it as a semantic scalpel.

Output ONLY valid JSON — no markdown, no explanation, no code blocks around it.
Schema:
{
  "summary": "one-line summary",
  "steps": ["step 1", "step 2", ...],
  "files_to_touch": ["relative/path/file.py", ...],
  "tests_to_run": ["pytest tests/", ...]
}
"""

_MAX_TREE_DEPTH = 3
_MAX_FILE_READ = 3000


class PlannerAgent:
    """Analyzes a repo and emits a structured PlanOutput."""

    def __init__(self, llm) -> None:
        self._llm = llm

    async def plan(self, task_description: str, toolkit: AgentToolkit) -> PlanOutput:
        """Generate an implementation plan for the given task."""
        context = self._gather_context(toolkit)
        prompt = (
            f"TASK:\n{task_description}\n\n"
            f"REPO CONTEXT:\n{context}\n\n"
            "Produce the JSON implementation plan now:"
        )

        from cortex.llm.router import IntentProfile

        raw = await self._llm.complete(
            prompt,
            system=_SYSTEM,
            temperature=0.2,
            max_tokens=1500,
            intent=IntentProfile.ARCHITECT,
        )

        return self._parse(raw)

    def _gather_context(self, toolkit: AgentToolkit) -> str:
        """Collect repo structure + key files for context."""
        parts: list[str] = []

        # Tree
        tree = self._tree(toolkit.repo_path, depth=_MAX_TREE_DEPTH)
        parts.append(f"TREE:\n{tree}")

        # README
        for name in ("README.md", "README.rst", "README.txt", "README"):
            content = toolkit.read_file(name)
            if not content.startswith("[ERROR]"):
                parts.append(f"README:\n{content[:_MAX_FILE_READ]}")
                break

        # pyproject / package.json
        for cfg in ("pyproject.toml", "package.json", "Cargo.toml", "go.mod"):
            content = toolkit.read_file(cfg)
            if not content.startswith("[ERROR]"):
                parts.append(f"{cfg.upper()}:\n{content[:1500]}")
                break

        # Recent git log
        parts.append(f"RECENT LOG:\n{toolkit.git_log(5)}")

        return "\n\n".join(parts)

    @staticmethod
    def _tree(root: Path, depth: int, prefix: str = "", current: int = 0) -> str:
        """Generate a directory tree string."""
        if current > depth:
            return ""
        lines: list[str] = []
        try:
            entries = sorted(root.iterdir())
        except PermissionError:
            return ""
        ignore = {
            ".git", "__pycache__", ".venv", "node_modules", ".build",
            "dist", ".mypy_cache", ".pytest_cache"
        }
        for e in entries:
            if e.name in ignore or e.name.startswith("."):
                continue
            lines.append(
                f"{prefix}{'└── ' if e == entries[-1] else '├── '}{e.name}{'/' if e.is_dir() else ''}"
            )
            if e.is_dir():
                ext = "    " if e == entries[-1] else "│   "
                lines.append(PlannerAgent._tree(e, depth, prefix + ext, current + 1))
        return "\n".join(line for line in lines if line)

    def _parse(self, raw: str) -> PlanOutput:
        """Parse JSON plan from LLM output, with fallback."""
        # Strip potential markdown fences
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1])

        try:
            data = json.loads(text)
            return PlanOutput(
                summary=data.get("summary", ""),
                steps=data.get("steps", []),
                files_to_touch=data.get("files_to_touch", []),
                tests_to_run=data.get("tests_to_run", ["pytest"]),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Planner JSON parse failed (%s) — using raw text as single step", e)
            return PlanOutput(
                summary="Plan extracted from raw LLM output",
                steps=[raw.strip()],
                files_to_touch=[],
                tests_to_run=["pytest"],
            )
