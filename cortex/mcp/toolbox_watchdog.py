"""CORTEX Toolbox Watchdog — Subprocess Lifecycle Manager.

Manages the genai-toolbox binary as a child process, auto-restarting
on crash with exponential backoff. Designed to co-run alongside
JosuProactiveDaemon.proactive_loop() as a sibling coroutine.

Architecture:
    ToolboxWatchdog.run()
      └─> _spawn_process()       # Launch genai-toolbox subprocess
            └─> _health_loop()   # Periodic health probes
                  └─> on failure: _restart_with_backoff()

Axiom Derivations:
    Ω₀ (Self-Reference): The system manages its own infrastructure.
    Ω₅ (Antifragile): Each crash forges a stronger restart strategy.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("cortex.mcp.toolbox_watchdog")

# ── Configuration ─────────────────────────────────────────────────

_DEFAULT_PORT = 5050
_HEALTH_INTERVAL_S = 30
_MAX_BACKOFF_S = 300  # 5 min cap
_INITIAL_BACKOFF_S = 2
_STARTUP_GRACE_S = 3

_TOOLS_YAML = Path(__file__).parent / "toolbox" / "tools.yaml"
_DEFAULT_DB = Path.home() / ".cortex" / "cortex.db"


# ── Watchdog ──────────────────────────────────────────────────────


class ToolboxWatchdog:
    """Manages genai-toolbox as a supervised child process.

    Usage:
        watchdog = ToolboxWatchdog()
        await watchdog.run()  # Blocks forever, restarts on crash
    """

    __slots__ = (
        "_port",
        "_tools_yaml",
        "_db_path",
        "_process",
        "_backoff",
        "_restart_count",
        "_shutdown",
        "_log_fd",
    )

    def __init__(
        self,
        port: int = _DEFAULT_PORT,
        tools_yaml: Optional[Path] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self._port = port
        self._tools_yaml = tools_yaml or _TOOLS_YAML
        self._db_path = db_path or Path(
            os.environ.get("CORTEX_DB", str(_DEFAULT_DB)),
        )
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._backoff = _INITIAL_BACKOFF_S
        self._restart_count = 0
        self._shutdown = False
        self._log_fd: Optional[Any] = None

    # ── Public API ────────────────────────────────────────────────

    async def run(self) -> None:
        """Main lifecycle loop. Spawn → monitor → restart."""
        binary = self._find_binary()
        if not binary:
            logger.error(
                "🚫 [WATCHDOG] genai-toolbox not found. "
                "Install: go install "
                "github.com/googleapis/genai-toolbox@latest",
            )
            return

        if not self._tools_yaml.exists():
            logger.error(
                "🚫 [WATCHDOG] tools.yaml not found at %s",
                self._tools_yaml,
            )
            return

        logger.info(
            "🔭 [WATCHDOG] Starting Toolbox supervisor (port=%d, db=%s)",
            self._port,
            self._db_path,
        )

        while not self._shutdown:
            try:
                self._spawn(binary)
                await self._health_loop()
            except asyncio.CancelledError:
                logger.info(
                    "🛑 [WATCHDOG] Shutdown signal received.",
                )
                self._shutdown = True
                self._kill()
                raise
            except Exception as exc:  # noqa: BLE001 — supervisor catches all crashes
                logger.error(
                    "☠️ [WATCHDOG] Crash detected: %s",
                    exc,
                )

            if not self._shutdown:
                self._restart_count += 1
                wait = min(
                    self._backoff * (2 ** (self._restart_count - 1)),
                    _MAX_BACKOFF_S,
                )
                logger.warning(
                    "♻️ [WATCHDOG] Restart #%d in %.0fs (backoff)",
                    self._restart_count,
                    wait,
                )
                await asyncio.sleep(wait)

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._shutdown = True
        self._kill()

    @property
    def is_alive(self) -> bool:
        """Check if the managed process is running."""
        return self._process is not None and self._process.poll() is None

    @property
    def restart_count(self) -> int:
        """Number of times the process has been restarted."""
        return self._restart_count

    # ── Internals ─────────────────────────────────────────────────

    def _find_binary(self) -> Optional[str]:
        """Locate genai-toolbox in PATH or ~/go/bin."""
        found = shutil.which("genai-toolbox")
        if found:
            return found

        go_bin = Path.home() / "go" / "bin" / "genai-toolbox"
        if go_bin.exists():
            return str(go_bin)

        return None

    def _rotate_logs(
        self,
        log_file: Path,
        max_bytes: int = 5 * 1024 * 1024,
        backups: int = 3,
    ) -> None:
        """Rotate logs if size exceeds max_bytes, keeping `backups` copies."""
        if not log_file.exists() or log_file.stat().st_size < max_bytes:
            return

        for i in range(backups - 1, 0, -1):
            src = log_file.with_name(f"{log_file.name}.{i}")
            dst = log_file.with_name(f"{log_file.name}.{i + 1}")
            if src.exists():
                shutil.move(str(src), str(dst))

        dst1 = log_file.with_name(f"{log_file.name}.1")
        shutil.move(str(log_file), str(dst1))

    def _spawn(self, binary: str) -> None:
        """Launch the genai-toolbox subprocess."""
        env = os.environ.copy()
        env["CORTEX_DB"] = str(self._db_path)

        cmd = [
            binary,
            "--tools-file",
            str(self._tools_yaml),
            "--port",
            str(self._port),
        ]

        log_dir = Path.home() / ".cortex" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "toolbox.log"
        self._rotate_logs(log_file)

        self._log_fd = open(log_file, "a")

        self._process = subprocess.Popen(
            cmd,
            env=env,
            stdout=self._log_fd,
            stderr=subprocess.STDOUT,
        )

        logger.info(
            "🚀 [WATCHDOG] Spawned PID %d: %s",
            self._process.pid,
            " ".join(cmd),
        )

    async def _health_loop(self) -> None:
        """Monitor process health with periodic probes."""
        # Grace period for startup
        await asyncio.sleep(_STARTUP_GRACE_S)

        if not self.is_alive:
            logger.error(
                "💀 [WATCHDOG] Process died during startup.",
            )
            return

        # Reset backoff on successful start
        self._backoff = _INITIAL_BACKOFF_S
        logger.info(
            "✅ [WATCHDOG] Toolbox alive (PID %d, port %d)",
            self._process.pid,  # type: ignore[union-attr]
            self._port,
        )

        while not self._shutdown:
            await asyncio.sleep(_HEALTH_INTERVAL_S)

            if not self.is_alive:
                rc = self._process.returncode if self._process else -1
                logger.warning(
                    "💀 [WATCHDOG] Process exited (rc=%s).",
                    rc,
                )
                return

            # HTTP health probe
            from cortex.mcp.toolbox_bridge import (
                toolbox_health_check,
            )

            if not toolbox_health_check(
                url=f"http://127.0.0.1:{self._port}",
            ):
                logger.warning(
                    "⚠️ [WATCHDOG] Health probe failed but process alive — possible hang.",
                )

    def _kill(self) -> None:
        """Terminate the managed process."""
        if self._process and self._process.poll() is None:
            logger.info(
                "🔪 [WATCHDOG] Terminating PID %d",
                self._process.pid,
            )
            self._process.send_signal(signal.SIGTERM)
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

        if self._log_fd:
            try:
                self._log_fd.close()
            except OSError:
                pass
            self._log_fd = None
