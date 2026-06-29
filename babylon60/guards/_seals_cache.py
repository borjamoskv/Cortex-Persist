# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from babylon60.guards._seal_printer import SealPrinter

ROOT_DIR = Path(__file__).resolve().parents[2]
printer = SealPrinter()
_VENV_BIN = Path(sys.executable).parent


def _resolve_cmd(tool: str) -> str:
    """Resolve a CLI tool: prefer .venv/bin, fall back to system PATH."""
    venv_path = _VENV_BIN / tool
    if venv_path.exists():
        return str(venv_path)
    return tool


async def arun_cmd(cmd: list[str], timeout: float = 60.0) -> tuple[int, str]:
    """Execute a command asynchronously and return (code, output).

    Injects PYTHONPATH=. to ensure local package resolution.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    resolved = [_resolve_cmd(cmd[0])] + cmd[1:]
    try:
        proc = await asyncio.create_subprocess_exec(
            *resolved,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, stdout.decode(errors="replace")
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except (ValueError, TypeError, KeyError, AssertionError) as exc:
                import logging

                logging.warning("Suppressed exception: %s", exc)
            return 124, f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return 127, f"Command not found: {resolved[0]}"


class GlobalSourceCache:
    """O(1) Memory Cache for Python Source Files to Annihilate Repeated O(N) Disk I/O."""

    _instance = None
    _loaded = False
    files: dict[Path, str] = {}

    def __new__(cls) -> GlobalSourceCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def load(cls) -> None:
        """Loads all Python files into memory concurrently. Called exactly once."""
        if cls._loaded:
            return

        cortex_dir = ROOT_DIR / "cortex"

        def _get_files() -> list[Path]:
            return [
                f for f in cortex_dir.rglob("*.py") if "test" not in str(f) and ".pyc" not in str(f)
            ]

        target_files = await asyncio.to_thread(_get_files)

        async def _read_file(p: Path) -> tuple[Path, str | None]:
            try:
                content = await asyncio.to_thread(p.read_text, encoding="utf-8")
                return p, content
            except OSError:
                return p, None

        results = await asyncio.gather(*(_read_file(p) for p in target_files))
        for p, content in results:
            if content is not None:
                cls.files[p] = content

        cls._loaded = True
