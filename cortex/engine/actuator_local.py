"""
CORTEX Native Actuator — Sovereign Host Access (Ω-Manus Architecture).

This module implements the Local Actuator, enabling CORTEX to perform
actions directly on the host system (files, shell, tools) under strict
ByzantineAuth and PrivacyGate governance.
"""

from __future__ import annotations

import asyncio
import asyncio.subprocess
import logging
import shutil
from pathlib import Path
from typing import Any

from cortex.engine.auth import ByzantineAuthLayer
from cortex.engine.signals import log_motor
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.engine.actuator")


class LocalActuator:
    """
    Sovereign handle for host-level operations.

    Every destructive action (write, execute, delete) must be authorized
    by ByzantineAuthLayer. Zero-trust by default.
    """

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.auth = ByzantineAuthLayer()

    async def write_file(
        self,
        filepath: str | Path,
        content: str,
        zenith_score: float = 0.0,
        project: str = "default",
    ) -> Result[Path, str]:
        """Write a file to the host system after authorization."""
        full_path = self.workspace_root / filepath
        payload = {
            "action": "FILE_WRITE",
            "path": str(full_path),
            "content_hash": hash(content),
            "project": project,
        }

        # [Ω₁] Byzantine Verification
        authorized = await self.auth.acquire_lock("FILE_WRITE", payload, zenith_score)
        if not authorized:
            return Err("Authorization REJECTED or TIMEOUT by ByzantineAuth.")

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            log_motor(f"Actuator: Escrito {full_path.name}", action="WRITE")
            return Ok(full_path)
        except OSError as e:
            return Err(f"System Error: {e}")

    async def shell_execute(
        self,
        command: str,
        args: list[str] | None = None,
        zenith_score: float = 0.0,
        project: str = "default",
    ) -> Result[dict[str, Any], str]:
        """Execute a shell command on the host system after authorization."""
        full_command = f"{command} {' '.join(args or [])}"
        payload = {
            "action": "SHELL_EXECUTE",
            "command": full_command,
            "project": project,
        }

        # [Ω₁] Byzantine Verification
        authorized = await self.auth.acquire_lock("OS_COMMAND", payload, zenith_score)
        if not authorized:
            return Err("Authorization REJECTED or TIMEOUT by ByzantineAuth.")

        try:
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root),
            )
            stdout, stderr = await process.communicate()

            log_motor(f"Actuator: Ejecutado '{command}'", action="EXEC")
            return Ok(
                {
                    "exit_code": process.returncode,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                }
            )
        except Exception as e:
            return Err(f"Execution Error: {e}")

    async def secure_handoff(
        self,
        sandbox_path: Path,
        host_path: Path,
        zenith_score: float = 0.0,
    ) -> Result[bool, str]:
        """Move a file/dir from a sandbox to the host after verification."""
        if not sandbox_path.exists():
            return Err("Source path does not exist in sandbox.")

        payload = {
            "action": "SECURE_HANDOFF",
            "from": str(sandbox_path),
            "to": str(host_path),
        }

        authorized = await self.auth.acquire_lock("SECURE_HANDOFF", payload, zenith_score)
        if not authorized:
            return Err("Handoff REJECTED.")

        try:
            if sandbox_path.is_dir():
                if host_path.exists():
                    shutil.rmtree(host_path)
                shutil.copytree(sandbox_path, host_path)
            else:
                host_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sandbox_path, host_path)

            log_motor(f"Actuator: Handoff {host_path.name} completado", action="HANDOFF")
            return Ok(True)
        except Exception as e:
            return Err(f"Handoff Error: {e}")


# Global Actuator Instance
NATIVE_ACTUATOR = LocalActuator()
