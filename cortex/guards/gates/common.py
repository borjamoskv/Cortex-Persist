# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Protocol, TypeAlias

from cortex.guards._seal_printer import SealPrinter

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
            # synchronous scan is unavoidable, but we do it only once
            return [
                f for f in cortex_dir.rglob("*.py") if "test" not in str(f) and ".pyc" not in str(f)
            ]

        target_files = await asyncio.to_thread(_get_files)

        async def _read_file(p: Path) -> tuple[Path, str | None]:
            try:
                # Use to_thread to prevent blocking event loop on disk I/O
                content = await asyncio.to_thread(p.read_text, encoding="utf-8")
                return p, content
            except OSError:
                return p, None

        results = await asyncio.gather(*(_read_file(f) for f in target_files))
        for p, content in results:
            if content is not None:
                cls.files[p] = content

        cls._loaded = True
        # print(f"   [CACHE] {len(cls.files)} files ingestion complete.")
