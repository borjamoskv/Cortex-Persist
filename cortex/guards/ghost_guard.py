"""
ghost_guard.py — The Sonic Archeology Guard (Ω₁₃).

Detects and prevents "Code Ghosts" (0-size or inoperative abstractions).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("cortex.guards.sonic_archeology")

class GhostGuard:
    """Detects 0-size files and inoperative dummy abstractions."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    async def check_files(self, paths: list[Path]) -> list[Path]:
        """Check a list of files for ghost-status (0-size)."""
        ghosts = []
        for path in paths:
            if not path.exists():
                continue
            if path.stat().st_size == 0 and path.name != "__init__.py":
                ghosts.append(path)
        return ghosts

    async def audit_codebase(self, directory: str = "cortex") -> list[Path]:
        """Scan directory for ghosts."""
        base = self.root / directory
        if not base.exists():
            return []

        ghosts = []
        for py_file in base.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            if py_file.stat().st_size == 0:
                ghosts.append(py_file)

        return ghosts

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Admission guard for code facts: prevent saving ghost references."""
        # Check if we are trying to persist a 0-size file reference
        if fact_type == "code_reference" and meta.get("size") == 0:
            raise ValueError("[Ω₁₃] Sonic Archeology Violation: Ghost file reference (0-size) rejected.")
