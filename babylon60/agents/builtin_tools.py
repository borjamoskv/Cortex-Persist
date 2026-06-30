# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Built-in Tools for Autonomous Agent.

Provides concrete Tool implementations for the AutonomousAgent's
ToolRegistry. Each tool follows the Tool protocol and can be
independently tested.

Tools included:
    - ShellTool: Execute shell commands (subprocess)
    - FileSystemTool: Read/write/list filesystem operations
    - HttpTool: HTTP requests (GET/POST)
    - ExergyAuditTool: Thermodynamic audit of agent state
    - NoOpTool: Passthrough tool for testing

All tools enforce C5-REAL execution: every invocation produces
real, verifiable side effects. No simulated output.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.agents.builtin_tools")


class ShellTool:
    """Execute shell commands with timeout and output capture.

    Reality Level: C5-REAL - commands execute on the host.
    """

    @property
    def name(self) -> str:
        return "shell"

    async def execute(
        self,
        *,
        cmd: str,
        cwd: str | None = None,
        timeout: float = 30.0,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Run a shell command and return stdout/stderr/returncode."""
        run_env = {**os.environ, **(env or {})}

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=run_env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:10_000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5_000],
                "success": proc.returncode == 0,
            }

        except asyncio.TimeoutError:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "success": False,
            }
        except (ValueError, KeyError, OSError) as exc:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "success": False,
            }


class FileSystemTool:
    """Read, write, list, and check filesystem paths.

    Reality Level: C5-REAL - operates on the real filesystem.
    """

    @property
    def name(self) -> str:
        return "filesystem"

    async def execute(
        self,
        *,
        action: str,
        path: str,
        content: str | None = None,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Execute a filesystem operation.

        Actions:
            read: Read file contents
            write: Write content to file (creates parent dirs)
            append: Append content to file
            exists: Check if path exists
            list: List directory contents
            stat: Get file metadata
            delete: Delete a file
        """
        target = Path(path)

        try:
            if action == "read":
                text = target.read_text(encoding=encoding)
                return {"ok": True, "content": text[:50_000], "size": len(text)}

            if action == "write":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content or "", encoding=encoding)
                return {"ok": True, "path": str(target), "bytes_written": len(content or "")}

            if action == "append":
                with target.open("a", encoding=encoding) as f:
                    f.write(content or "")
                return {"ok": True, "path": str(target)}

            if action == "exists":
                return {"ok": True, "exists": target.exists(), "is_file": target.is_file()}

            if action == "list":
                if not target.is_dir():
                    return {"ok": False, "error": f"Not a directory: {path}"}
                entries = [
                    {
                        "name": e.name,
                        "is_dir": e.is_dir(),
                        "size": e.stat().st_size if e.is_file() else None,
                    }
                    for e in sorted(target.iterdir())
                    if not e.name.startswith(".")
                ]
                return {"ok": True, "entries": entries[:200], "total": len(entries)}

            if action == "stat":
                if not target.exists():
                    return {"ok": False, "error": f"Path not found: {path}"}
                st = target.stat()
                return {
                    "ok": True,
                    "size": st.st_size,
                    "modified": st.st_mtime,
                    "is_file": target.is_file(),
                    "is_dir": target.is_dir(),
                }

            if action == "delete":
                if target.is_file():
                    target.unlink()
                    return {"ok": True, "deleted": str(target)}
                return {"ok": False, "error": "Can only delete files"}

            return {"ok": False, "error": f"Unknown action: {action}"}

        except (ValueError, KeyError, OSError) as exc:
            return {"ok": False, "error": str(exc)}


class HttpTool:
    """Make HTTP requests using aiohttp or urllib fallback.

    Reality Level: C5-REAL - makes real network requests.
    """

    @property
    def name(self) -> str:
        return "http"

    async def execute(
        self,
        *,
        method: str = "GET",
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """Execute an HTTP request."""
        import aiohttp

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers or {},
                    data=body,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response,
            ):
                response_body = await response.text()
                return {
                    "ok": True,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": response_body[:20_000],
                }

        except aiohttp.ClientResponseError as exc:
            return {
                "ok": False,
                "status": exc.status,
                "error": str(exc),
                "body": "",
            }
        except (ValueError, KeyError, OSError, aiohttp.ClientError) as exc:
            return {"ok": False, "error": str(exc)}


class ExergyAuditTool:
    """Audit the thermodynamic state of agent execution.

    Reads the current plan and computes exergy efficiency ratios.
    Does not produce side effects - pure observation.
    """

    @property
    def name(self) -> str:
        return "exergy_audit"

    async def execute(
        self,
        *,
        plan_summary: dict[str, Any] | None = None,
        agent_telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Audit exergy metrics and return diagnostic report."""
        if not plan_summary:
            return {"ok": True, "status": "NO_PLAN", "recommendation": "idle"}

        exergy = plan_summary.get("net_exergy", 0)
        entropy = plan_summary.get("entropy_paid", 0)
        progress = plan_summary.get("progress", "0%")

        # Efficiency ratio
        efficiency = exergy / max(entropy, 0.001)

        # Diagnostic
        if efficiency > 2.0:
            status = "OPTIMAL"
            recommendation = "continue"
        elif efficiency > 1.0:
            status = "HEALTHY"
            recommendation = "continue"
        elif efficiency > 0.5:
            status = "DEGRADED"
            recommendation = "reduce_entropy"
        else:
            status = "CRITICAL"
            recommendation = "halt_and_reassess"

        return {
            "ok": True,
            "status": status,
            "efficiency": round(efficiency, 4),
            "net_exergy": exergy,
            "entropy_paid": entropy,
            "progress": progress,
            "recommendation": recommendation,
        }


class NoOpTool:
    """Passthrough tool for testing and plan validation."""

    @property
    def name(self) -> str:
        return "noop"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Return kwargs as-is."""
        return {"ok": True, "echo": kwargs}


class GitTool:
    """Git operations for autonomous code management.

    Reality Level: C5-REAL - executes real git commands.
    """

    @property
    def name(self) -> str:
        return "git"

    async def execute(
        self,
        *,
        action: str,
        repo_path: str,
        args: str = "",
    ) -> dict[str, Any]:
        """Execute git operations.

        Actions: status, add, commit, push, pull, clone, diff, log, branch
        """
        shell = ShellTool()

        if action == "clone":
            return await shell.execute(cmd=f"git clone {args} {repo_path}")

        cmd_map = {
            "status": "git status --porcelain",
            "add": f"git add {args or '.'}",
            "commit": f"git commit -m {args!r}" if args else "git commit --allow-empty -m 'auto'",
            "push": f"git push {args}",
            "pull": f"git pull {args}",
            "diff": f"git diff {args}",
            "log": f"git log --oneline -n 10 {args}",
            "branch": f"git branch {args}",
        }

        cmd = cmd_map.get(action)
        if not cmd:
            return {"ok": False, "error": f"Unknown git action: {action}"}

        return await shell.execute(cmd=cmd, cwd=repo_path)


class ApexKnowledgeTool:
    """Query the 100 Sovereign APEX Primitives registry.

    Reality Level: C5-REAL - loads from the centralized registry.
    """

    @property
    def name(self) -> str:
        return "apex_knowledge"

    async def execute(
        self, *, action: str = "lookup", apex_id: str | None = None
    ) -> dict[str, Any]:
        """Query the APEX registry.

        Actions:
            list: Return IDs and names of all 100 primitives.
            lookup: Return full details (Trigger, Execute, Verify, Fail) for a specific apex_id.
        """
        from babylon60.agents.primitives.registry import apex_registry

        if action == "list":
            return {
                "ok": True,
                "primitives": [
                    {"id": p.id, "name": p.name} for p in apex_registry.list_primitives()
                ],
            }
        elif action == "lookup":
            if not apex_id:
                return {"ok": False, "error": "apex_id is required for lookup"}
            prim = apex_registry.get_primitive(apex_id)
            if not prim:
                return {"ok": False, "error": f"Primitive {apex_id} not found."}
            return {"ok": True, "primitive": prim}

        return {"ok": False, "error": f"Unknown action: {action}"}


def register_all_builtin_tools(registry: Any) -> None:
    """Register all built-in tools into a ToolRegistry."""
    tools = [
        ShellTool(),
        FileSystemTool(),
        HttpTool(),
        ExergyAuditTool(),
        NoOpTool(),
        GitTool(),
        ApexKnowledgeTool(),
    ]
    for tool in tools:
        registry.register(tool)
    logger.info("Registered %d built-in tools: %s", len(tools), [t.name for t in tools])
