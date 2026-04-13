"""Native conflict arbiter for epistemic integrity checks."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from cortex.core.paths import resolve_native_binary


class NativeArbiter:
    """Axiom Ω0: direct-silicon bypass for epistemic integrity."""

    def __init__(self, binary_path: str | None = None) -> None:
        resolved = (
            Path(binary_path).expanduser()
            if binary_path is not None
            else resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN")
        )
        self.binary_path = str(resolved) if resolved is not None else None
        self._available = resolved is not None

    def check(self, subject_hash: str) -> str | None:
        """Run the native conflict checker synchronously."""
        if not self._available:
            return None
        binary_path = self.binary_path
        if binary_path is None:
            return None
        try:
            result = subprocess.run(
                [binary_path, "check", subject_hash],
                capture_output=True,
                text=True,
                timeout=0.1,
                check=False,
            )
            output = result.stdout.strip()
            if output.startswith("CONFLICT:"):
                return output.replace("CONFLICT:", "")
            return None
        except (FileNotFoundError, OSError, subprocess.SubprocessError, UnicodeError):
            return None

    async def check_async(self, subject_hash: str) -> str | None:
        """Run the native conflict check without blocking the event loop."""
        return await asyncio.to_thread(self.check, subject_hash)
