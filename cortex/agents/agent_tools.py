"""CORTEX Agent Runtime — Built-in Tools for Autonomous Agents.

Provides file editing, terminal execution, test running, and git
operations as Tool protocol implementations. All tools are sandboxed
to a working directory and enforce timeouts.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.agents.agent_tools")

__all__ = [
    "FileReadTool",
    "FileWriteTool",
    "GitTool",
    "TerminalTool",
    "TestRunnerTool",
    "register_builtin_tools",
]

# ── Constants ────────────────────────────────────────────────────

DEFAULT_TERMINAL_TIMEOUT: float = 30.0
DEFAULT_TEST_TIMEOUT: float = 120.0
MAX_OUTPUT_BYTES: int = 50_000


# ── Helpers ──────────────────────────────────────────────────────


async def _run_subprocess(
    *args: str,
    cwd: str | None = None,
    timeout: float = DEFAULT_TERMINAL_TIMEOUT,
) -> tuple[int, str, str]:
    """Run a subprocess with timeout. Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(
            f"Command timed out after {timeout}s: {' '.join(args[:3])}"
        ) from None

    stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
    stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
    return proc.returncode or 0, stdout, stderr


def _validate_path(file_path: str, workdir: str | None = None) -> Path:
    """Validate and resolve a file path, ensuring it stays within workdir."""
    path = Path(file_path).resolve()
    if workdir:
        workdir_path = Path(workdir).resolve()
        if not str(path).startswith(str(workdir_path)):
            raise PermissionError(
                f"Path {path} is outside working directory {workdir_path}"
            )
    return path


# ── FileReadTool ─────────────────────────────────────────────────


class FileReadTool:
    """Read file contents. Implements Tool protocol."""

    def __init__(self, workdir: str | None = None) -> None:
        self._workdir = workdir

    @property
    def name(self) -> str:
        return "file_read"

    async def execute(self, **kwargs: Any) -> Any:
        """Read a file's contents.

        Args:
            path: File path to read.
            start_line: Optional 1-indexed start line.
            end_line: Optional 1-indexed end line.
        """
        file_path = kwargs.get("path", "")
        if not file_path:
            raise ValueError("'path' argument is required")

        path = _validate_path(file_path, self._workdir)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = path.read_text(encoding="utf-8", errors="replace")

        start = kwargs.get("start_line")
        end = kwargs.get("end_line")

        if start is not None or end is not None:
            lines = content.splitlines(keepends=True)
            s = max(0, (start or 1) - 1)
            e = end or len(lines)
            content = "".join(lines[s:e])

        return {"path": str(path), "content": content[:MAX_OUTPUT_BYTES]}


# ── FileWriteTool ────────────────────────────────────────────────


class FileWriteTool:
    """Write or patch file contents. Implements Tool protocol."""

    def __init__(self, workdir: str | None = None) -> None:
        self._workdir = workdir

    @property
    def name(self) -> str:
        return "file_write"

    async def execute(self, **kwargs: Any) -> Any:
        """Write content to a file.

        Args:
            path: File path to write.
            content: Full content to write.
            create_dirs: Whether to create parent directories (default True).
        """
        file_path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        create_dirs = kwargs.get("create_dirs", True)

        if not file_path:
            raise ValueError("'path' argument is required")

        path = _validate_path(file_path, self._workdir)

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        logger.info("FileWriteTool: wrote %d bytes to %s", len(content), path)

        return {
            "path": str(path),
            "bytes_written": len(content),
            "created": True,
        }


# ── TerminalTool ─────────────────────────────────────────────────


class TerminalTool:
    """Execute shell commands with timeout. Implements Tool protocol."""

    def __init__(
        self,
        workdir: str | None = None,
        timeout: float = DEFAULT_TERMINAL_TIMEOUT,
    ) -> None:
        self._workdir = workdir
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "terminal"

    async def execute(self, **kwargs: Any) -> Any:
        """Execute a shell command.

        Args:
            command: Shell command string to execute.
            timeout: Optional override for timeout in seconds.
        """
        command = kwargs.get("command", "")
        if not command:
            raise ValueError("'command' argument is required")

        timeout = kwargs.get("timeout", self._timeout)
        cwd = self._workdir or os.getcwd()

        logger.info(
            "TerminalTool: executing in %s: %.80s",
            cwd,
            command,
        )

        returncode, stdout, stderr = await _run_subprocess(
            "sh", "-c", command,
            cwd=cwd,
            timeout=timeout,
        )

        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "success": returncode == 0,
        }


# ── TestRunnerTool ───────────────────────────────────────────────


class TestRunnerTool:
    """Run pytest and parse results. Implements Tool protocol."""

    def __init__(
        self,
        workdir: str | None = None,
        timeout: float = DEFAULT_TEST_TIMEOUT,
    ) -> None:
        self._workdir = workdir
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "test_runner"

    async def execute(self, **kwargs: Any) -> Any:
        """Run pytest on a target path.

        Args:
            path: Test file or directory (default: "tests/").
            args: Additional pytest arguments.
        """
        test_path = kwargs.get("path", "tests/")
        extra_args = kwargs.get("args", [])
        cwd = self._workdir or os.getcwd()

        cmd_parts = ["python", "-m", "pytest", test_path, "-v", "--tb=short"]
        cmd_parts.extend(extra_args)

        logger.info("TestRunnerTool: running in %s: %s", cwd, " ".join(cmd_parts))

        returncode, stdout, stderr = await _run_subprocess(
            *cmd_parts,
            cwd=cwd,
            timeout=self._timeout,
        )

        passed = returncode == 0
        output = stdout + stderr

        return {
            "passed": passed,
            "returncode": returncode,
            "output": output[:MAX_OUTPUT_BYTES],
            "test_path": test_path,
        }


# ── GitTool ──────────────────────────────────────────────────────


class GitTool:
    """Git operations: status, add, commit, diff, branch. Implements Tool protocol."""

    def __init__(self, workdir: str | None = None) -> None:
        self._workdir = workdir

    @property
    def name(self) -> str:
        return "git"

    async def execute(self, **kwargs: Any) -> Any:
        """Execute a git operation.

        Args:
            action: One of 'status', 'add', 'commit', 'diff', 'branch'.
            files: List of files (for add).
            message: Commit message (for commit).
            branch_name: Branch name (for branch create).
        """
        action = kwargs.get("action", "status")
        cwd = self._workdir or os.getcwd()

        if action == "status":
            rc, out, err = await _run_subprocess(
                "git", "status", "--porcelain", cwd=cwd
            )
            return {"action": "status", "output": out, "clean": not out.strip()}

        if action == "add":
            files = kwargs.get("files", ["."])
            rc, out, err = await _run_subprocess(
                "git", "add", *files, cwd=cwd
            )
            return {"action": "add", "success": rc == 0, "output": out + err}

        if action == "commit":
            message = kwargs.get("message", "Agent commit")
            rc, out, err = await _run_subprocess(
                "git", "commit", "-m", message, cwd=cwd
            )
            return {
                "action": "commit",
                "success": rc == 0,
                "output": out + err,
            }

        if action == "diff":
            rc, out, err = await _run_subprocess("git", "diff", cwd=cwd)
            return {"action": "diff", "output": out}

        if action == "branch":
            branch_name = kwargs.get("branch_name", "")
            if branch_name:
                rc, out, err = await _run_subprocess(
                    "git", "checkout", "-b", branch_name, cwd=cwd
                )
                return {
                    "action": "branch_create",
                    "success": rc == 0,
                    "output": out + err,
                }
            rc, out, err = await _run_subprocess(
                "git", "branch", "--list", cwd=cwd
            )
            return {"action": "branch_list", "output": out}

        raise ValueError(f"Unknown git action: {action}")


# ── Registry Helper ──────────────────────────────────────────────


def register_builtin_tools(
    registry: Any,
    workdir: str | None = None,
) -> None:
    """Register all built-in agent tools into a ToolRegistry."""
    registry.register(FileReadTool(workdir))
    registry.register(FileWriteTool(workdir))
    registry.register(TerminalTool(workdir))
    registry.register(TestRunnerTool(workdir))
    registry.register(GitTool(workdir))
    logger.info(
        "Registered %d built-in tools (workdir=%s)",
        5,
        workdir or "cwd",
    )
