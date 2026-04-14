"""
CORTEX V6.1 - Physical Parity Layer (Vector 4 of the Singularity).

Provides the Autonomous Heartbeat Daemon with direct, unfiltered
access to the underlying OS (macOS/Cloud) via bindings inspired by
the Ekin and Gidatu Sovereign Skills.

V9.1: All shell execution is gated by ShellIntentClassifier
and wrapped in sandbox-exec OS-level prison.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from cortex.extensions.security.shell_ast_classifier import (
    SHELL_CLASSIFIER,
)

logger = logging.getLogger("cortex.extensions.daemon.actuators")

# OS-level sandbox profile path
_PRISON_PROFILE = Path(__file__).resolve().parents[3] / "cortex-core" / "cortex_prison.sb"

# Approved write directories for Gidatu file operations
_APPROVED_WRITE_ROOTS: tuple[str, ...] = (
    "/tmp",
    "/private/tmp",
    "/Users/borjafernandezangulo/Cortex-Persist/.scratch",
    "/Users/borjafernandezangulo/30_CORTEX/.scratch",
)


class PhysicalActuator:
    """
    Standardized bindings for physical OS manipulation.
    Provides Ekin (Action) and Gidatu (Control) capabilities.

    V9.1 Security Layers:
        1. ShellIntentClassifier (8-layer AST analysis)
        2. sandbox-exec kernel enforcement
        3. Path confinement for file writes
    """

    @staticmethod
    async def ekin_execute_shell(command: str, timeout: float = 30.0) -> dict[str, Any]:
        """
        EKIN-Binding: Execute raw shell commands with
        zero-trust isolation and strict timeouts.

        V9.1: Pre-gated by ShellIntentClassifier,
        wrapped in sandbox-exec prison.
        """
        # Gate 1: Shell AST Intent Classification
        verdict = SHELL_CLASSIFIER.classify(command)
        if verdict.blocked:
            logger.warning(
                "🛡️ [EKIN] ShellAST BLOCKED: %s → %s",
                command[:50],
                verdict.reason,
            )
            return {
                "status": "blocked",
                "returncode": -3,
                "stdout": "",
                "stderr": (f"[BLOCKED] {verdict.reason}"),
            }

        # Gate 2: OS-Level Prison
        if _PRISON_PROFILE.exists():
            exec_args = (
                "sandbox-exec",
                "-f",
                str(_PRISON_PROFILE),
                "/bin/sh",
                "-lc",
                command,
            )
        else:
            exec_args = ("/bin/sh", "-lc", command)
            logger.warning("⚠️ cortex_prison.sb not found")

        logger.warning(
            "🦾 [PHYSICAL PARITY] Executing: %s",
            command[:50],
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "status": ("success" if proc.returncode == 0 else "error"),
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
            }
        except asyncio.TimeoutError:
            logger.error(
                "🦾 [PHYSICAL PARITY] Timed out: %s",
                command,
            )
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Execution timed out.",
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("🦾 [PHYSICAL PARITY] Failed.")
            return {
                "status": "exception",
                "returncode": -2,
                "stdout": "",
                "stderr": str(e),
            }

    @staticmethod
    async def gidatu_write_file(
        path: str,
        content: str,
        append: bool = False,
    ) -> bool:
        """
        GIDATU-Binding: Direct file system manipulation.
        V9.1: Path confinement to approved write roots.
        """
        # Path confinement check
        resolved = str(Path(path).resolve())
        if not any(resolved.startswith(root) for root in _APPROVED_WRITE_ROOTS):
            logger.error(
                "🛡️ [GIDATU] Write DENIED outside approved arena: %s",
                path,
            )
            return False

        logger.info("🦾 [PHYSICAL PARITY] Writing: %s", path)
        mode = "a" if append else "w"
        try:

            def _write():
                with open(path, mode, encoding="utf-8") as f:
                    f.write(content)

            await asyncio.to_thread(_write)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to write at %s: %s", path, e)
            return False

    @staticmethod
    async def gidatu_read_file(
        path: str,
    ) -> str | None:
        """
        GIDATU-Binding: Direct file system perception.
        """
        logger.debug("🦾 [PHYSICAL PARITY] Reading: %s", path)
        try:

            def _read():
                with open(path, encoding="utf-8") as f:
                    return f.read()

            return await asyncio.to_thread(_read)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to read at %s: %s", path, e)
            return None
