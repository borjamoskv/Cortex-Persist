# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""CORTEX v5.2 — Sovereign Syscalls (EXOSKELETON).

Centralizes all host-level interactions for agents.
Implements Axiom Ω₃ (Byzantine Default) by enforcing argument lists
over shell strings and validating sandbox boundaries.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

logger = logging.getLogger("cortex.sys")


class SovereignSys:
    """Sovereign System Interface.

    All agents must use this interface instead of raw os/subprocess.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _is_safe(self, path: str | Path) -> bool:
        """Verify that a path is within the sovereign root (sandbox)."""
        try:
            target = (self.root / path).resolve()
            return self.root in target.parents or target == self.root
        except (OSError, ValueError):
            return False

    def bash(self, args: Sequence[str], timeout: int = 60) -> str:
        """Execute a command via argument list (No shell injection).

        Args:
            args: Command and arguments as a sequence.
            timeout: Execution timeout in seconds.

        Returns:
            Combined stdout and stderr.
        """
        logger.info("🔧 [SYS] Executing: %s", " ".join(args))
        try:
            result = subprocess.run(
                args,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # Hard requirement: no shell interpolation
                check=False,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
            )
            return (result.stdout + result.stderr).strip()
        except subprocess.TimeoutExpired:
            return f"[ERROR] Command timed out after {timeout}s"
        except (FileNotFoundError, PermissionError, OSError) as e:
            return f"[ERROR] Execution failed: {e}"

    def read(self, rel_path: str | Path) -> str:
        """Read a file within the sandbox."""
        if not self._is_safe(rel_path):
            return f"[ERROR] Access denied: {rel_path} is outside sandbox."

        try:
            return (self.root / rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return f"[ERROR] Read failed: {e}"

    def write(self, rel_path: str | Path, content: str) -> str:
        """Write a file within the sandbox."""
        if not self._is_safe(rel_path):
            return f"[ERROR] Access denied: {rel_path} is outside sandbox."

        target = self.root / rel_path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"[SUCCESS] Wrote to {rel_path}"
        except OSError as e:
            return f"[ERROR] Write failed: {e}"

    def list_dir(self, rel_path: str | Path = ".") -> str:
        """List directory contents within the sandbox."""
        if not self._is_safe(rel_path):
            return f"[ERROR] Access denied: {rel_path} is outside sandbox."

        try:
            target = self.root / rel_path
            entries = []
            for item in sorted(target.iterdir()):
                rel = item.relative_to(self.root)
                tag = "/" if item.is_dir() else ""
                entries.append(f"{rel}{tag}")
            return "\n".join(entries) or "(empty)"
        except OSError as e:
            return f"[ERROR] List failed: {e}"
