# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Protocol, TypeAlias

from cortex.guards._seal_printer import SealPrinter
from cortex.guards._seals_cache import GlobalSourceCache

__all__ = [
    "GateResult",
    "GateCallable",
    "printer",
    "ROOT_DIR",
    "arun_cmd",
    "GlobalSourceCache",
]

# ── Type Definitions ──
# Result: (Success, Reason/Status)
GateResult: TypeAlias = tuple[bool, str]


class GateCallable(Protocol):
    async def __call__(self) -> GateResult: ...


# ── Constants ──
printer = SealPrinter()
ROOT_DIR = Path(__file__).resolve().parents[3]
_VENV_BIN = ROOT_DIR / ".venv" / "bin"


def _resolve_cmd(tool: str) -> str:
    """Resolve a CLI tool: prefer .venv/bin, fall back to sys.executable or system PATH."""
    venv_path = _VENV_BIN / tool
    if venv_path.exists():
        return str(venv_path)

    # If it's a python tool (fallback for restricted environments)
    if tool in ("python", "python3"):
        return sys.executable

    # Fallback to system PATH
    return tool


async def arun_cmd(cmd: list[str], cwd: Path = ROOT_DIR) -> tuple[int, str]:
    """Run a subprocess asynchronously and return (exit_code, output)."""
    resolved = [_resolve_cmd(cmd[0])] + cmd[1:]
    try:
        proc = await asyncio.create_subprocess_exec(
            *resolved,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return proc.returncode or 0, stdout.decode(errors="replace")
    except FileNotFoundError:
        return 127, f"Command not found: {resolved[0]}"
