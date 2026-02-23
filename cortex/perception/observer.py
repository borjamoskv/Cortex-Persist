"""
CORTEX v5.0 — Perception Layer 1: File Activity Observer.

Watches workspace via watchdog FSEvents with debouncing.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from cortex.perception_base import (
    DEBOUNCE_SECONDS,
    FileEvent,
    classify_file,
    infer_project_from_path,
    should_ignore,
)

__all__ = ["FileActivityObserver"]

logger = logging.getLogger("cortex.perception")


class _DebouncedHandler(FileSystemEventHandler):
    """Watchdog handler with debouncing for rapid file changes."""

    def __init__(
        self,
        callback: Callable[[FileEvent], None],
        workspace: str,
        debounce_s: float = DEBOUNCE_SECONDS,
    ) -> None:
        super().__init__()
        self.callback = callback
        self.workspace = workspace
        self.debounce_s = debounce_s
        self._last_events: dict[str, float] = {}

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = str(event.src_path)
        if should_ignore(path):
            return

        now = time.monotonic()
        last = self._last_events.get(path, 0)
        if now - last < self.debounce_s:
            return  # debounced

        self._last_events[path] = now

        # Classify
        ev_type = (
            event.event_type
            if event.event_type in {"created", "modified", "deleted", "moved"}
            else "modified"
        )
        role = classify_file(path)
        project = infer_project_from_path(path, self.workspace)

        fe = FileEvent(
            path=path,
            event_type=ev_type,
            role=role,
            project=project,
            timestamp=now,
        )
        self.callback(fe)

    def cleanup_old_entries(self, max_age: float = 600) -> None:
        """Remove old debounce entries to prevent memory leak."""
        now = time.monotonic()
        expired = [k for k, v in self._last_events.items() if now - v > max_age]
        for k in expired:
            del self._last_events[k]


class FileActivityObserver:
    """Watches a workspace directory for file changes via FSEvents.

    Usage:
        observer = FileActivityObserver("/path/to/workspace")
        observer.start()
        # ... events flow to the callback
        observer.stop()
    """

    def __init__(
        self,
        workspace: str,
        callback: Callable[[FileEvent], None],
        debounce_s: float = DEBOUNCE_SECONDS,
        recursive: bool = True,
    ) -> None:
        self.workspace = workspace
        self.handler = _DebouncedHandler(callback, workspace, debounce_s)
        self._observer = Observer()
        self._observer.schedule(self.handler, workspace, recursive=recursive)

    def start(self) -> None:
        """Start watching the filesystem."""
        self._observer.start()
        logger.info("FileActivityObserver started: %s", self.workspace)

    def stop(self) -> None:
        """Stop watching the filesystem."""
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("FileActivityObserver stopped")

    @property
    def is_alive(self) -> bool:
        return self._observer.is_alive()
