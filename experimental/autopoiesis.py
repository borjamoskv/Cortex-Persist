# autopoiesis.py
"""Autopoiesis module.

Provides the `Autopoiesis` class that can generate, test, and register new
utility scripts on‑the‑fly inside a sandboxed Docker environment. The workflow
mirrors the *self‑creation* concept from the design document: when the agent
needs a capability it writes a Python script, runs it, validates the output and
stores the script for future reuse.

The sandbox implementation here is a very thin wrapper around the `subprocess`
module that runs `docker run` with a minimal Python image. In a production
system you would use a dedicated sandbox service (e.g., `popen` with resource
limits, `firejail`, or a cloud function).
"""

from __future__ import annotations
import os
import subprocess
import uuid
from pathlib import Path
from typing import Callable, Optional


class Autopoiesis:
    """Self‑creation engine for on‑demand tools.

    The class assumes a writable directory ``self.tool_dir`` where generated
    scripts are stored. Each script is given a unique name based on a UUID to
    avoid collisions.
    """

    def __init__(self, tool_dir: str | os.PathLike = "./generated_tools") -> None:
        self.tool_dir = Path(tool_dir)
        self.tool_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    def _docker_run(self, script_path: Path) -> subprocess.CompletedProcess:
        """Execute a Python script inside a minimal Docker container.

        The container uses the official ``python:3.12-slim`` image. The script is
        mounted read‑only and the working directory is set to ``/app``.
        """
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{script_path.resolve()}:/app/script.py:ro",
            "python:3.12-slim",
            "python",
            "/app/script.py",
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    # ---------------------------------------------------------------------
    def generate_and_register(
        self,
        generator: Callable[[], str],
        validator: Optional[Callable[[str], bool]] = None,
    ) -> Path:
        """Generate a script, execute it in the sandbox, and register it.

        Parameters
        ----------
        generator: Callable[[], str]
            Function that returns the full source code of the script.
        validator: Callable[[str], bool] | None
            Optional function that receives the script stdout and returns ``True``
            if the result is acceptable.

        Returns
        -------
        Path
            Path to the stored script file.
        """
        source = generator()
        script_name = f"tool_{uuid.uuid4().hex[:8]}.py"
        script_path = self.tool_dir / script_name
        script_path.write_text(source, encoding="utf-8")

        # Run inside Docker sandbox
        result = self._docker_run(script_path)
        if result.returncode != 0:
            raise RuntimeError(f"Sandbox execution failed: {result.stderr}")

        if validator is not None and not validator(result.stdout):
            raise ValueError("Validator rejected script output")

        # Successful registration – keep the script file for future use
        return script_path

    # ---------------------------------------------------------------------
    def list_registered(self) -> list[Path]:
        """Return a list of all generated tool scripts."""
        return list(self.tool_dir.glob("tool_*.py"))

    # ---------------------------------------------------------------------
    def remove_tool(self, script_path: Path) -> None:
        """Delete a previously generated tool script."""
        try:
            script_path.unlink()
        except FileNotFoundError:
            pass

# Example usage (remove before production)
if __name__ == "__main__":
    ap = Autopoiesis()
    def gen():
        return "print('Hello from sandbox')"
    path = ap.generate_and_register(gen)
    print(f"Generated tool stored at {path}")
```
