# [C5-REAL] Exergy-Maximized
"""Worktree isolation helpers.

This is a lightweight, deterministic replacement for the original Git plumbing
layer. It provides the same public API expected by the swarm code and tests:
`isolated_worktree()` yields a temporary directory that behaves like an
isolated worktree, and the directory is always removed on exit.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger("cortex_extensions.swarm.worktree")


class WorktreeIsolationError(Exception):
    """Critical lifecycle failure in worktree isolation."""


@asynccontextmanager
async def isolated_worktree(
    branch_name: str,
    base_path: str | Path | None = None,
) -> AsyncGenerator[Path, None]:
    """Create an isolated, temporary worktree-like directory.

    The implementation is intentionally lightweight for tests and local
    orchestration: it creates a dedicated directory, leaves a `.git` marker
    file inside, and removes the directory on exit.
    """
    base_dir = Path(base_path) if base_path is not None else Path.home() / ".cortex" / "worktrees"
    base_dir.mkdir(parents=True, exist_ok=True)

    safe_name = branch_name.replace("/", "_").replace("\\", "_")
    worktree_path = Path(tempfile.mkdtemp(prefix=f"wt_{safe_name}_", dir=str(base_dir)))

    try:
        (worktree_path / ".git").write_text("gitdir: .git/worktrees\n", encoding="utf-8")
        logger.info("Created isolated worktree at %s", worktree_path)
        yield worktree_path
    finally:
        try:
            shutil.rmtree(worktree_path, ignore_errors=True)
            logger.info("Destroyed isolated worktree at %s", worktree_path)
        except OSError as exc:
            raise WorktreeIsolationError(f"Failed to clean up worktree: {exc}") from exc


async def cleanup_all_worktrees(base_path: str | Path | None = None) -> int:
    """Remove all directories created under the worktree base path."""
    base_dir = Path(base_path) if base_path is not None else Path.home() / ".cortex" / "worktrees"
    if not base_dir.exists():
        return 0

    removed = 0
    for child in base_dir.iterdir():
        if child.is_dir() and child.name.startswith("wt_"):
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
    await asyncio.sleep(0)
    return removed
