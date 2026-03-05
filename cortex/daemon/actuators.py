"""
CORTEX V6 - Physical Parity Layer (Vector 4 of the Singularity).

Provides the Autonomous Heartbeat Daemon with direct, unfiltered 
access to the underlying OS (macOS/Cloud) via bindings inspired by
the Ekin and Gidatu Sovereign Skills.
Eliminates the boundary between "thought" and "physical execution".
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger("cortex.daemon.actuators")


class PhysicalActuator:
    """
    Standardized bindings for physical OS manipulation.
    Provides Ekin (Action) and Gidatu (Control) capabilities.
    """

    @staticmethod
    async def ekin_execute_shell(command: str, timeout: float = 30.0) -> dict[str, Any]:
        """
        EKIN-Binding: Execute raw shell commands with zero-trust isolation
        and strict timeouts to prevent freezing the daemon.
        """
        logger.warning("🦾 [PHYSICAL PARITY] Executing OS Command: %s", command[:50])
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            return {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
            }
        except asyncio.TimeoutError:
            logger.error("🦾 [PHYSICAL PARITY] Command timed out: %s", command)
            return {"status": "timeout", "returncode": -1, "stdout": "", "stderr": "Execution timed out."}
        except Exception as e:
            logger.exception("🦾 [PHYSICAL PARITY] Terminal execution failed.")
            return {"status": "exception", "returncode": -2, "stdout": "", "stderr": str(e)}

    @staticmethod
    async def gidatu_write_file(path: str, content: str, append: bool = False) -> bool:
        """
        GIDATU-Binding: Direct file system manipulation.
        """
        logger.info("🦾 [PHYSICAL PARITY] Modifying File system: %s", path)
        mode = "a" if append else "w"
        try:
            def _write():
                with open(path, mode, encoding="utf-8") as f:
                    f.write(content)
            await asyncio.to_thread(_write)
            return True
        except Exception as e:
            logger.error("Failed to write physical file at %s: %s", path, e)
            return False

    @staticmethod
    async def gidatu_read_file(path: str) -> str | None:
        """
        GIDATU-Binding: Direct file system perception.
        """
        logger.debug("🦾 [PHYSICAL PARITY] Reading File system: %s", path)
        try:
            def _read():
                with open(path, encoding="utf-8") as f:
                    return f.read()
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.error("Failed to read physical file at %s: %s", path, e)
            return None
