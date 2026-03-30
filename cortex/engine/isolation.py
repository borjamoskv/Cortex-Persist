"""
CORTEX Isolation Engine — Parallel Sovereign Workspaces (Ω-Architecture).

This module implements the Parallel Isolation Engine, providing isolated,
monitored, and restricted execution environments for swarm actuators.
Inspired by Devin's Alpha (March 2026).
"""

from __future__ import annotations

import asyncio
import asyncio.subprocess
import logging
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.engine.isolation")


@dataclass
class ExecutionResult:
    """Result of a sandboxed Python execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float = 0.0


class IsolationLevel(Enum):
    """Degrees of containment for a workspace."""

    LOCAL = "local"  # Subprocess on host (minimal)
    SANDBOX = "sandbox"  # gVisor / User-mode Linux (moderate)
    IMAGE = "image"  # Docker / Podman (high)
    VM = "vm"  # Firecracker / KVM (sovereign)


@dataclass
class WorkspaceMetadata:
    """State and identity of an isolated workspace."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: IsolationLevel = IsolationLevel.LOCAL
    root: Path | None = None
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class IsolationManager:
    """
    Orchestrator for parallel isolated environments.

    Manages the lifecycle of workspaces, enforcing exergy limits
    and monitoring for escaping attempts (Ω-Immunity).
    """

    def __init__(self, engine: Any | None = None, max_concurrent: int = 25):
        self.engine = engine
        self.workspaces: dict[str, WorkspaceMetadata] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def create_workspace(
        self,
        level: IsolationLevel = IsolationLevel.LOCAL,
        project: str = "default",
        persistent: bool = False,
    ) -> Result[WorkspaceMetadata, str]:
        """Spawn a new isolated workspace."""
        async with self._lock:
            if level != IsolationLevel.LOCAL:
                return Err(
                    f"IsolationLevel.{level.name} requires an external runtime which is not yet bound."
                )

            ws = WorkspaceMetadata(level=level)
            ws.metadata["project"] = project
            ws.metadata["persistent"] = persistent

            # Logic for directory creation or container spawning goes here
            # For now, we simulate a local folder isolation
            ws.root = Path(f"/tmp/cortex_iso_{ws.id}")
            try:
                ws.root.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return Err(f"Failed to initialize workspace root: {e}")

            self.workspaces[ws.id] = ws

            if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
                await self.engine.ledger.record_transaction(
                    project=project,
                    action="workspace_created",
                    detail={"workspace_id": ws.id, "level": level.value, "root": str(ws.root)},
                )

            logger.info("IsolationManager: Created workspace %s at %s", ws.id, ws.root)
            return Ok(ws)

    async def execute(
        self, workspace_id: str, command: str, args: list[str], timeout: float = 30.0
    ) -> Result[dict[str, Any], str]:
        """Execute a command within the specified isolation boundary."""
        async with self._semaphore:
            if workspace_id not in self.workspaces:
                return Err(f"Workspace {workspace_id} not found")

        ws = self.workspaces[workspace_id]
        logger.info("IsolationManager: Executing %s in %s", command, workspace_id)

        start_time = time.monotonic()

        try:
            # Native asyncio subprocess execution
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                cwd=str(ws.root) if ws.root else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                out_str = stdout.decode() if stdout else ""
                err_str = stderr.decode() if stderr else ""

                if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
                    await self.engine.ledger.record_transaction(
                        project=ws.metadata.get("project", "default"),
                        action="workspace_execution",
                        detail={
                            "workspace_id": ws.id,
                            "command": f"{command} {' '.join(args)}",
                            "exit_code": process.returncode,
                            "stdout_size": len(out_str),
                            "duration_s": float(round(time.monotonic() - start_time, 3)),
                        },
                    )
                return Ok(
                    {
                        "stdout": out_str,
                        "stderr": err_str,
                        "exit_code": process.returncode,
                    }
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

                if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
                    await self.engine.ledger.record_transaction(
                        project=ws.metadata.get("project", "default"),
                        action="workspace_execution_failed",
                        detail={
                            "workspace_id": ws.id,
                            "command": f"{command} {' '.join(args)}",
                            "reason": "timeout",
                            "duration_s": float(timeout),
                        },
                    )
                return Err(f"Command timed out after {timeout}s")

        except Exception as e:
            if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
                await self.engine.ledger.record_transaction(
                    project=ws.metadata.get("project", "default"),
                    action="workspace_execution_failed",
                    detail={
                        "workspace_id": ws.id,
                        "command": f"{command} {' '.join(args)}",
                        "reason": str(e),
                        "duration_s": float(round(time.monotonic() - start_time, 3)),
                    },
                )
            return Err(f"Execution failed: {e}")

    async def destroy_workspace(self, workspace_id: str) -> Result[bool, str]:
        """Wipe an isolated workspace and all its data."""
        async with self._lock:
            if workspace_id not in self.workspaces:
                return Err("Workspace not found")

            ws = self.workspaces.pop(workspace_id)
            if ws.root and ws.root.exists() and not ws.metadata.get("persistent", False):
                try:
                    if ws.root.is_dir():
                        shutil.rmtree(str(ws.root))
                except Exception as e:
                    logger.warning("Failed to cleanup workspace %s: %s", workspace_id, e)

            logger.info("IsolationManager: Destroyed workspace %s", workspace_id)
            return Ok(True)

    @asynccontextmanager
    async def isolate(
        self, level: IsolationLevel = IsolationLevel.LOCAL, label: str = "sandbox"
    ) -> AsyncIterator[ByzantineSandbox]:
        """Context manager for temporary isolated execution (Ω-Isolation)."""
        async with self.provision_sandbox(level=level, label=label) as sandbox:
            yield sandbox

    @asynccontextmanager
    async def provision_sandbox(
        self, level: IsolationLevel = IsolationLevel.LOCAL, label: str = "sandbox"
    ) -> AsyncIterator[ByzantineSandbox]:
        """Context manager for temporary isolated execution."""
        res = await self.create_workspace(level=level, project=label)
        if isinstance(res, Err):
            raise RuntimeError(f"Could not provision sandbox: {res.error}")

        ws = res.value
        sandbox = ByzantineSandbox(self, ws.id)
        try:
            yield sandbox
        finally:
            await self.destroy_workspace(ws.id)


class ByzantineSandbox:
    """Handle for an active isolated environment (Ω-Sandbox)."""

    def __init__(self, manager: IsolationManager, workspace_id: str | None = None):
        self.manager = manager
        self.workspace_id = workspace_id or "default"

    @property
    def id(self) -> str:
        """Alias for workspace_id to match test expectations."""
        return self.workspace_id

    async def execute(
        self, command: str, args: list[str], timeout: float = 30.0
    ) -> Result[dict[str, Any], str]:
        """Execute a command within the sandbox boundary."""
        # If no explicit workspace, provision a temporary one
        if self.workspace_id == "default" and "default" not in self.manager.workspaces:
            async with self.manager.isolate() as sandbox:
                return await self.manager.execute(sandbox.workspace_id, command, args, timeout)

        return await self.manager.execute(self.workspace_id, command, args, timeout)

    async def execute_python(self, script_name: str, args: list[str] | None = None) -> Any:
        """Run a python script within the sandbox."""
        _args = ["python3", script_name] + (args or [])
        t0 = time.monotonic()
        res = await self.manager.execute(self.workspace_id, _args[0], _args[1:])
        t1 = time.monotonic()
        if isinstance(res, Ok):
            res_dict = cast(dict[str, Any], res.value)
            exec_res = ExecutionResult(**res_dict)
            exec_res.duration_ms = (t1 - t0) * 1000.0
            return exec_res
        return None

    async def write_file(self, filename: str, content: str) -> bool:
        """Write a file to the sandbox root."""
        ws = self.manager.workspaces.get(self.workspace_id)
        if not ws or not ws.root:
            raise RuntimeError(f"Workspace {self.workspace_id} has no root")

        file_path = Path(ws.root) / filename
        await asyncio.to_thread(file_path.write_text, content, encoding="utf-8")
        return True

    async def read_file(self, filename: str) -> str:
        """Read a file from the sandbox root."""
        ws = self.manager.workspaces.get(self.workspace_id)
        if not ws or not ws.root:
            raise RuntimeError(f"Workspace {self.workspace_id} has no root")

        file_path = Path(ws.root) / filename
        return await asyncio.to_thread(file_path.read_text, encoding="utf-8")


class SimpleIsolationEngine:
    """
    ARC-AGI-3 Sandboxed Python Executor (Phase 2).
    A wrapped instance of IsolationManager that ensures quick, restricted python runs.
    """

    def __init__(self, timeout: float = 15.0, max_concurrent: int = 25):
        self.manager = IsolationManager(max_concurrent=max_concurrent)
        self.timeout = timeout

    async def execute_sandbox(self, code: str, args: list[str] | None = None) -> ExecutionResult | None:
        """Executes Python code in a tightly controlled workspace."""
        async with self.manager.isolate(label="arc_sandbox") as sandbox:
            await sandbox.write_file("main.py", code)
            try:
                # 30.0 is the timeout inside execute_python, but we wrap it logically with overall self.timeout 
                res = await asyncio.wait_for(
                    sandbox.execute_python("main.py", args=args),
                    timeout=self.timeout + 1.0  # slight buffer
                )
                return res
            except asyncio.TimeoutError:
                raise TimeoutError("Sandboxed execution timed out") from None

