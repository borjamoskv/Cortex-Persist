"""monitor.py

MemoryPressureMonitor — Compaction Sidecar, Nivel 130/100.

Responsibilities:
- Periodic memory-pressure sampling via `psutil` (cross-platform) and
  `memory_wrapper.malloc_trim` / `mallinfo2` (Linux/glibc only, gracefully
  degraded on macOS with zero import-time side-effects).
- Runs OS calls in a ``ThreadPoolExecutor`` (not Process) — avoids fork
  hazards with SQLite connections on macOS and eliminates spawn overhead.
- Emits ``MemoryPressureAlert`` dataclass instances; caller routes them.
- Fully self-contained: no daemon-level imports, injected dependencies only.
- Named distinctly from ``CompactionMonitor`` (semantic DB compactor in
  ``cortex.daemon.monitors.compaction``) to prevent confusion.

Design decisions:
- ThreadPoolExecutor instead of ProcessPoolExecutor: psutil and ctypes are
  safe to run in threads; subprocess fork on macOS (spawn context) adds
  ~80ms latency per tick and risks BrokenProcessPool on SQLite file handles.
- Lazy imports inside worker functions: memory_wrapper uses ctypes.CDLL at
  import time; importing at module level would make the sidecar un-loadable
  on non-Linux systems if libc.so.6 is absent.
- asyncio.get_running_loop() instead of deprecated get_event_loop().
- legion import failure → WARNING (not DEBUG) to surface misconfiguration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("compaction-sidecar")

# ── Platform capability flags (cheap, no I/O) ────────────────────────────────
_PLATFORM = platform.system()
_IS_LINUX = _PLATFORM == "Linux"

# Probe psutil availability without importing at module level in workers
try:
    import psutil as _psutil_probe  # type: ignore[import]  # noqa: F401

    _HAS_PSUTIL: bool = True
except ModuleNotFoundError:
    _HAS_PSUTIL = False
    logger.debug("psutil not installed — memory pressure sampling will use fallback")


# ── MemorySnapshot ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MemorySnapshot:
    """Cross-platform memory pressure snapshot (immutable, thread-safe)."""

    rss_bytes: int = 0  # Resident Set Size of current process
    vms_bytes: int = 0  # Virtual Memory Size
    system_available_bytes: int = 0  # OS-level available physical memory
    system_total_bytes: int = 0  # OS-level total physical memory
    malloc_arena_bytes: int = 0  # glibc main arena size (Linux only)
    malloc_free_bytes: int = 0  # glibc fast/free bytes (Linux only)
    platform: str = ""

    @property
    def free_ratio(self) -> float:
        """system_available / system_total. Returns 1.0 (healthy) when no data."""
        if not self.system_total_bytes:
            return 1.0
        return self.system_available_bytes / self.system_total_bytes

    @property
    def malloc_free_ratio(self) -> float:
        """glibc free / arena. Returns 1.0 (healthy) on non-Linux / no data."""
        if not self.malloc_arena_bytes:
            return 1.0
        return self.malloc_free_bytes / self.malloc_arena_bytes

    @property
    def rss_mb(self) -> float:
        return self.rss_bytes / 1_048_576


# ── MemoryPressureAlert ───────────────────────────────────────────────────────


@dataclass
class MemoryPressureAlert:
    """Emitted when memory pressure crosses configured thresholds."""

    reason: str
    snapshot: MemorySnapshot
    threshold_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def message(self) -> str:
        return (
            f"[MemoryPressure:{self.threshold_name}] {self.reason} "
            f"| sys_free={self.snapshot.free_ratio:.1%} "
            f"| rss={self.snapshot.rss_mb:.1f}MB "
            f"| malloc_free={self.snapshot.malloc_free_ratio:.1%}"
        )


# ── Worker functions (run in ThreadPoolExecutor) ──────────────────────────────
# NOTE: These functions are called from threads, not coroutines. They must be
# synchronous, avoid asyncio, and handle all exceptions internally.


def _collect_snapshot() -> MemorySnapshot:
    """Collect memory stats from the current thread context (thread-safe)."""
    rss = vms = sys_avail = sys_total = arena = free_b = 0

    if _HAS_PSUTIL:
        try:
            import psutil as _p  # noqa: PLC0415

            mi = _p.Process(os.getpid()).memory_info()
            rss, vms = mi.rss, mi.vms
            vm = _p.virtual_memory()
            sys_avail, sys_total = vm.available, vm.total
        except Exception:  # noqa: BLE001 — boundary; caller handles alerts
            pass

    if _IS_LINUX:
        # Lazy import: ctypes.CDLL("libc.so.6") only attempted on Linux
        try:
            from cortex.daemon.sidecar.compaction_monitor.memory_wrapper import (  # noqa: PLC0415
                get_mallinfo2,
            )

            info = get_mallinfo2()
            arena, free_b = info.arena, info.fordblks
        except Exception:  # noqa: BLE001
            pass

    return MemorySnapshot(
        rss_bytes=rss,
        vms_bytes=vms,
        system_available_bytes=sys_avail,
        system_total_bytes=sys_total,
        malloc_arena_bytes=arena,
        malloc_free_bytes=free_b,
        platform=_PLATFORM,
    )


def _do_malloc_trim() -> bool:
    """Attempt malloc_trim(0) — Linux only. Returns True on success."""
    if not _IS_LINUX:
        return False
    try:
        from cortex.daemon.sidecar.compaction_monitor.memory_wrapper import (  # noqa: PLC0415
            malloc_trim,
        )

        malloc_trim(0)
        return True
    except Exception:  # noqa: BLE001
        return False


# ── MemoryPressureMonitor ─────────────────────────────────────────────────────

AlertCallback = Callable[[MemoryPressureAlert], Coroutine[Any, Any, None]]


class MemoryPressureMonitor:
    """Async sidecar that samples OS memory pressure and triggers malloc_trim.

    Distinct from ``CompactionMonitor`` (semantic DB compactor).
    This monitor operates at the OS/allocator level, not the CORTEX DB level.

    Parameters
    ----------
    interval:
        Poll interval in seconds. Default 5.0.
    sys_free_threshold:
        Emit alert when system free ratio < threshold. Default 0.15 (15%).
    malloc_free_threshold:
        Emit alert when glibc malloc free/arena ratio < threshold. Default 0.10.
        Only relevant on Linux; effectively disabled on macOS (ratio always 1.0).
    alert_callback:
        Async callable ``async def cb(alert: MemoryPressureAlert) -> None``.
        If None, alerts are logged as WARNING only.
    use_legion:
        Send alerts to Legion swarm via ``legion.send_alert`` (lazy import).
    max_workers:
        Thread pool size. Default 1 — one background thread is sufficient.
    """

    def __init__(
        self,
        *,
        interval: float = 5.0,
        sys_free_threshold: float = 0.15,
        malloc_free_threshold: float = 0.10,
        alert_callback: AlertCallback | None = None,
        use_legion: bool = False,
        max_workers: int = 1,
    ) -> None:
        self.interval = interval
        self.sys_free_threshold = sys_free_threshold
        self.malloc_free_threshold = malloc_free_threshold
        self._alert_callback = alert_callback
        self.use_legion = use_legion
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="compaction-sidecar"
        )
        self._running = False
        self._task: asyncio.Task[None] | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Schedule the monitoring coroutine on *loop* (or the running loop).

        Safe to call multiple times — idempotent.
        """
        if self._running:
            return
        self._running = True
        lp = loop or asyncio.get_event_loop()
        self._task = lp.create_task(self._loop(), name="memory-pressure-sidecar")
        logger.info("MemoryPressureMonitor started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        """Cancel the task and shut down the thread pool. Idempotent."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        logger.info("MemoryPressureMonitor stopped")

    async def sample(self) -> MemorySnapshot:
        """One-shot snapshot — useful for CLI inspection or tests."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, _collect_snapshot)

    # ── Internal loop ─────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                self._running = False
                raise
            except Exception as exc:  # noqa: BLE001 — top-level resilience
                logger.exception("MemoryPressureSidecar tick error: %s", exc)
            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                self._running = False
                raise

    async def _tick(self) -> None:
        loop = asyncio.get_running_loop()

        snapshot: MemorySnapshot = await loop.run_in_executor(self._executor, _collect_snapshot)

        alerts: list[MemoryPressureAlert] = []

        if snapshot.free_ratio < self.sys_free_threshold:
            alerts.append(
                MemoryPressureAlert(
                    reason=(
                        f"System free memory critical: {snapshot.free_ratio:.1%} "
                        f"({snapshot.system_available_bytes // 1_048_576}MB available)"
                    ),
                    snapshot=snapshot,
                    threshold_name="sys_free",
                )
            )

        if snapshot.malloc_free_ratio < self.malloc_free_threshold:
            alerts.append(
                MemoryPressureAlert(
                    reason=f"glibc arena exhausted: free={snapshot.malloc_free_ratio:.1%}",
                    snapshot=snapshot,
                    threshold_name="malloc_free",
                )
            )

        if alerts:
            trimmed: bool = await loop.run_in_executor(self._executor, _do_malloc_trim)
            logger.info(
                "malloc_trim: %s (Linux=%s)",
                "released pages" if trimmed else "N/A",
                _IS_LINUX,
            )
            for alert in alerts:
                await self._dispatch(alert)

    async def _dispatch(self, alert: MemoryPressureAlert) -> None:
        logger.warning(alert.message)
        if self._alert_callback is not None:
            await self._alert_callback(alert)
        if self.use_legion:
            try:
                from legion import send_alert  # type: ignore[import]  # noqa: PLC0415

                await send_alert(alert.message)
            except ImportError:
                # WARNING not DEBUG — misconfigured use_legion=True should be visible
                logger.warning("use_legion=True but 'legion' is not installed; alert dropped")


# ── Backward-compat alias ─────────────────────────────────────────────────────
# Keep old name importable during transition; will be removed in v7.
AsyncCompactionMonitor = MemoryPressureMonitor
