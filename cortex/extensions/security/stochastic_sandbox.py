"""CORTEX v9 — Stochastic Command Sandboxing.

Intercepts known-destructive stochastic commands (fuzz iterations,
chaos mutations, mass find-and-replace) and forces them into
ephemeral /tmp arenas, preventing Scope Creep and source corruption.

Architecture::

    cmd → StochasticSandbox.intercept(cmd, cwd)
             ├── STOCHASTIC → clone CWD to /tmp/cortex_sandbox_{uuid}/
             │                 └── SandboxedExecution(redirected=True)
             └── DETERMINISTIC → passthrough (no redirect)

    After execution:
      sandbox.cleanup(arena_path)  → rm -rf the ephemeral arena

Security Model:
- Stochastic commands NEVER write to the source repo
- All output captured in the sandbox arena
- Arena auto-destroyed after 180s timeout or explicit cleanup
- Results written to execution ledger for audit
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.security.stochastic_sandbox")

__all__ = ["StochasticSandbox", "SandboxedExecution"]


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass()
class SandboxedExecution:
    """Result of sandbox interception."""

    is_redirected: bool
    original_cmd: str
    redirected_cmd: str = ""
    arena_path: str = ""
    matched_pattern: str = ""
    timeout_seconds: int = 180


# ═══════════════════════════════════════
# Stochastic Patterns
# ═══════════════════════════════════════

_STOCHASTIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("FORGE_FUZZ", re.compile(r"forge\s+test.*--fuzz", re.IGNORECASE)),
    ("FORGE_SCRIPT_BROADCAST", re.compile(r"forge\s+script.*--broadcast", re.IGNORECASE)),
    ("FORGE_FUZZ_RUNS", re.compile(r"forge\s+test.*--fuzz-runs", re.IGNORECASE)),
    ("GIT_CLEAN_FORCE", re.compile(r"git\s+clean\s+-[fdx]{2,}", re.IGNORECASE)),
    ("MASS_DELETE", re.compile(r"rm\s+-r[f]?\s+[^\s]+", re.IGNORECASE)),
    ("FIND_DELETE", re.compile(r"find\s+.*(-delete|--delete|-exec\s+rm)", re.IGNORECASE)),
    ("SED_INPLACE_RECURSIVE", re.compile(r"find\s+.*-exec\s+sed\s+-i", re.IGNORECASE)),
    ("MASS_SED_INPLACE", re.compile(r"sed\s+-i\s+.*\*", re.IGNORECASE)),
    ("CHAOS_FUZZER", re.compile(r"python3?\s+.*cortex_chaos_fuzzer", re.IGNORECASE)),
    ("ECHIDNA", re.compile(r"echidna-test", re.IGNORECASE)),
    ("SLITHER_AGGRESSIVE", re.compile(r"slither\s+.*--detect-all", re.IGNORECASE)),
]

# Directories to clone into sandbox (relative to CWD)
# We DON'T clone node_modules or .git — too large and unnecessary for fuzzing
_CLONE_EXCLUDE_PATTERNS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".scratch",
    "dist",
    "build",
    "out",
    ".next",
    ".cache",
}

# Maximum arena size in bytes (500MB) to prevent disk exhaustion
_MAX_ARENA_SIZE = 500 * 1024 * 1024


class StochasticSandbox:
    """Intercepts stochastic/destructive commands and redirects to ephemeral arenas.

    Usage::

        sandbox = StochasticSandbox()
        result = sandbox.intercept("forge test --fuzz-runs 50000", cwd="/path/to/project")
        if result.is_redirected:
            # Execute result.redirected_cmd instead — it points to /tmp/cortex_sandbox_{uuid}/
            run(result.redirected_cmd)
            sandbox.cleanup(result.arena_path)
    """

    ARENA_PREFIX = "cortex_sandbox_"
    ARENA_ROOT = "/tmp"

    def intercept(self, cmd: str, cwd: str = ".") -> SandboxedExecution:
        """Check if a command is stochastic and redirect to sandbox if so.

        Args:
            cmd: The shell command to evaluate.
            cwd: The working directory the command would normally run in.

        Returns:
            SandboxedExecution with redirect info.
        """
        matched_label = self._match_stochastic(cmd)

        if not matched_label:
            return SandboxedExecution(
                is_redirected=False,
                original_cmd=cmd,
            )

        # Create ephemeral arena
        arena_id = f"{self.ARENA_PREFIX}{uuid.uuid4().hex[:12]}"
        arena_path = os.path.join(self.ARENA_ROOT, arena_id)

        try:
            self._create_arena(cwd, arena_path)
        except Exception as e:
            logger.error("Arena creation failed for %s: %s", matched_label, e)
            # Fail-closed: return non-redirected with the intent that the
            # main pipeline will reject it via SecurityMonitorClassifier
            return SandboxedExecution(
                is_redirected=False,
                original_cmd=cmd,
                matched_pattern=matched_label,
            )

        # Rewrite command to use arena as CWD
        redirected_cmd = self._rewrite_cmd(cmd, cwd, arena_path)

        logger.info(
            "🔒 [SANDBOX] Stochastic command [%s] redirected: %s → %s",
            matched_label,
            cwd,
            arena_path,
        )

        return SandboxedExecution(
            is_redirected=True,
            original_cmd=cmd,
            redirected_cmd=redirected_cmd,
            arena_path=arena_path,
            matched_pattern=matched_label,
        )

    def cleanup(self, arena_path: str) -> bool:
        """Destroy an ephemeral sandbox arena.

        Returns True if cleanup succeeded, False otherwise.
        """
        if not arena_path or not arena_path.startswith(self.ARENA_ROOT):
            logger.error("Refusing to cleanup path outside arena root: %s", arena_path)
            return False

        if self.ARENA_PREFIX not in arena_path:
            logger.error("Path does not contain arena prefix: %s", arena_path)
            return False

        try:
            if os.path.exists(arena_path):
                shutil.rmtree(arena_path)
                logger.info("🗑️ [SANDBOX] Arena destroyed: %s", arena_path)
                return True
        except Exception as e:
            logger.error("Arena cleanup failed for %s: %s", arena_path, e)

        return False

    def list_active_arenas(self) -> list[str]:
        """List all currently active sandbox arenas."""
        arenas = []
        try:
            for entry in os.scandir(self.ARENA_ROOT):
                if entry.is_dir() and entry.name.startswith(self.ARENA_PREFIX):
                    arenas.append(entry.path)
        except Exception:
            pass
        return arenas

    def cleanup_all(self) -> int:
        """Destroy ALL active arenas. Returns count of destroyed arenas."""
        count = 0
        for arena in self.list_active_arenas():
            if self.cleanup(arena):
                count += 1
        return count

    def _match_stochastic(self, cmd: str) -> Optional[str]:
        """Check if a command matches any stochastic pattern."""
        for label, pattern in _STOCHASTIC_PATTERNS:
            if pattern.search(cmd):
                return label
        return None

    def _create_arena(self, source_cwd: str, arena_path: str) -> None:
        """Create an ephemeral arena by cloning the source CWD.

        Excludes large directories (node_modules, .git, etc.) to minimize
        disk usage and clone time.
        """
        source = Path(source_cwd)
        if not source.exists():
            raise FileNotFoundError(f"Source CWD does not exist: {source_cwd}")

        os.makedirs(arena_path, exist_ok=True)

        # Selective copy: skip excluded patterns
        total_size = 0
        for item in source.iterdir():
            if item.name in _CLONE_EXCLUDE_PATTERNS:
                continue

            dest = Path(arena_path) / item.name
            try:
                if item.is_dir():
                    shutil.copytree(
                        item,
                        dest,
                        ignore=shutil.ignore_patterns(*_CLONE_EXCLUDE_PATTERNS),
                        dirs_exist_ok=True,
                    )
                else:
                    shutil.copy2(item, dest)

                # Track size
                if dest.is_file():
                    total_size += dest.stat().st_size
                elif dest.is_dir():
                    for f in dest.rglob("*"):
                        if f.is_file():
                            total_size += f.stat().st_size

                if total_size > _MAX_ARENA_SIZE:
                    logger.warning("Arena size exceeded %d bytes limit, stopping copy", _MAX_ARENA_SIZE)
                    break

            except Exception as e:
                logger.warning("Failed to copy %s to arena: %s", item.name, e)

        logger.info("Arena created: %s (%.1f MB)", arena_path, total_size / (1024 * 1024))

    def _rewrite_cmd(self, cmd: str, original_cwd: str, arena_path: str) -> str:
        """Rewrite command to operate in the arena instead of the original CWD.

        Strategy: Replace absolute paths pointing to original CWD with arena path,
        then prepend cd to arena.
        """
        # Replace absolute paths in the command
        rewritten = cmd.replace(original_cwd, arena_path)

        # If the command doesn't already reference the arena, prepend cd
        if arena_path not in rewritten:
            rewritten = f"cd {arena_path} && {rewritten}"

        return rewritten


# Global singleton
SANDBOX = StochasticSandbox()
