# [C5-REAL] Exergy-Maximized
"""WatchdogHub - Unified filesystem monitor for the daemon.

Consolidates Git watching & AST monitoring into a single Observer
that publishes events to the DistributedEventBus.

Uses kernel-level kqueue (macOS) / inotify (Linux) via watchdog
for O(1) event-driven detection - no polling.

Architecture:
    ┌─────────────────────────────────────┐
    │  WatchdogHub                         │
    │  ┌──────────┐  ┌────────────────┐   │
    │  │ Observer  │→ │ UnifiedHandler │   │
    │  │ (kqueue)  │  │ filter+debounce│   │
    │  └──────────┘  └───────┬────────┘   │
    │                        │             │
    │              EventBus.publish()      │
    │              HotStateDB.increment()  │
    └─────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from pathlib import Path
from typing import Any

try:
    from watchdog.events import (  # pyright: ignore[reportAssignmentType]
        FileSystemEvent,  # type: ignore
        FileSystemEventHandler,  # type: ignore
    )
    from watchdog.observers import Observer  # pyright: ignore[reportAssignmentType]

    _WATCHDOG_AVAILABLE = True
except ImportError:

    class FileSystemEventHandler:  # type: ignore[no-redef]
        """Stub for missing watchdog."""

    class FileSystemEvent:  # type: ignore[no-redef]
        """Stub."""

        src_path: str = ""

    class Observer:  # type: ignore[no-redef]
        """Stub."""

        def schedule(self, *a, **kw):
            """Stub method to schedule observation."""

        def start(self):
            """Stub method to start observation."""

        def stop(self):
            """Stub method to stop observation."""

        def join(self):
            """Stub method to join observer thread."""

    _WATCHDOG_AVAILABLE = False

logger = logging.getLogger("babylon60.daemon.watchers")

__all__ = ["WatchdogHub"]

# Default patterns to watch
DEFAULT_PATTERNS = ["*.py", "*.md", "*.json", "*.yaml", "*.yml", "*.toml"]

# Directories always excluded from watching
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".ruff_cache",
    ".pytest_cache",
    "venv",
    ".mypy_cache",
}

# Debounce window: ignore duplicate events within this many seconds
DEBOUNCE_SECONDS = 1.0


class _UnifiedHandler(FileSystemEventHandler):
    """Handles filesystem events with pattern filtering & debounce."""

    def __init__(
        self,
        patterns: list[str],
        event_bus: Any | None,
        hot_state: Any | None,
        loop: asyncio.AbstractEventLoop | None,
    ) -> None:
        self._patterns = patterns
        self._event_bus = event_bus
        self._hot_state = hot_state
        self._loop = loop
        self._last_events: dict[str, float] = {}

    def _should_handle(self, path: str) -> bool:
        """Check pattern match and debounce."""
        p = Path(path)

        # Exclude dirs
        for part in p.parts:
            if part in EXCLUDE_DIRS:
                return False

        # Pattern match
        if not any(fnmatch.fnmatch(p.name, pat) for pat in self._patterns):
            return False

        # Debounce
        now = time.monotonic()
        last = self._last_events.get(path, 0)
        if now - last < DEBOUNCE_SECONDS:
            return False
        self._last_events[path] = now
        return True

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:  # pyright: ignore[reportAttributeAccessIssue]
            return
        if self._should_handle(event.src_path):
            self._emit("fs.modified", event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:  # pyright: ignore[reportAttributeAccessIssue]
            return
        if self._should_handle(event.src_path):
            self._emit("fs.created", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:  # pyright: ignore[reportAttributeAccessIssue]
            return
        if self._should_handle(event.src_path):
            self._emit("fs.deleted", event.src_path)

    def _emit(self, topic: str, path: str) -> None:
        """Publish event to bus and update hot state."""
        payload = {
            "path": path,
            "filename": Path(path).name,
            "source": "watchdog-hub",
            "timestamp": time.monotonic(),
        }

        logger.debug("%s: %s", topic, path)

        # Update hot state counter
        if self._hot_state is not None:
            try:
                self._hot_state.increment("fs_events_total")
                self._hot_state.set(
                    f"fs:last:{topic}",
                    payload,
                    ttl_s=3600,
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("UnifiedHandler hot state increment/set failed: %s", e, exc_info=True)

        # Publish to event bus (thread-safe via run_coroutine_threadsafe)
        if self._event_bus is not None and self._loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._event_bus.publish(topic, payload),
                    self._loop,
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("UnifiedHandler event bus publish failed: %s", e, exc_info=True)


class WatchdogHub:
    """Unified filesystem monitor using kernel-level watchdog.

    Usage:
        hub = WatchdogHub(
            paths=["~/Cortex-Persist", "~/.agent"],
            event_bus=bus,
            hot_state=state,
        )
        await hub.start()

        # ... hub publishes fs.modified/created/deleted to EventBus ...

        await hub.stop()
    """

    __slots__ = (
        "_event_bus",
        "_handler",
        "_hot_state",
        "_observer",
        "_paths",
        "_patterns",
        "_running",
    )

    def __init__(
        self,
        paths: list[str | Path] | None = None,
        patterns: list[str] | None = None,
        event_bus: Any | None = None,
        hot_state: Any | None = None,
    ) -> None:
        self._paths = [Path(p).expanduser().resolve() for p in (paths or [])]
        self._patterns = patterns or DEFAULT_PATTERNS
        self._event_bus = event_bus
        self._hot_state = hot_state
        self._observer: Observer | None = None
        self._handler: _UnifiedHandler | None = None
        self._running = False

    async def start(self) -> None:
        """Start watching configured paths."""
        if not _WATCHDOG_AVAILABLE:
            logger.warning("watchdog not installed - WatchdogHub disabled")
            return

        if not self._paths:
            logger.info("No paths configured - WatchdogHub idle")
            return

        loop = asyncio.get_running_loop()
        self._handler = _UnifiedHandler(
            patterns=self._patterns,
            event_bus=self._event_bus,
            hot_state=self._hot_state,
            loop=loop,
        )

        self._observer = Observer()
        for path in self._paths:
            if path.exists() and path.is_dir():
                self._observer.schedule(
                    self._handler,
                    str(path),
                    recursive=True,
                )
                logger.info("Watching: %s (%s)", path, ", ".join(self._patterns))
            else:
                logger.warning("Watch path does not exist: %s", path)

        self._observer.start()
        self._running = True
        logger.info(
            "WatchdogHub started - %d paths, %d patterns",
            len(self._paths),
            len(self._patterns),
        )

    async def stop(self) -> None:
        """Stop watching."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5.0)  # pyright: ignore[reportCallIssue]
            self._observer = None
        self._running = False
        logger.info("WatchdogHub stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def add_path(self, path: str | Path) -> None:
        """Add a path to watch (takes effect on next start)."""
        resolved = Path(path).expanduser().resolve()
        if resolved not in self._paths:
            self._paths.append(resolved)
            # If already running, hot-schedule
            if self._observer is not None and self._handler is not None:
                if resolved.exists() and resolved.is_dir():
                    self._observer.schedule(
                        self._handler,
                        str(resolved),
                        recursive=True,
                    )
                    logger.info("Hot-added watch path: %s", resolved)
