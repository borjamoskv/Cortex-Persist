"""Base class and common utilities for daemon monitors (PULMONES)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger("moskv-daemon")


class BaseMonitor(ABC, Generic[T]):
    """Abstract base for all MOSKV monitors."""

    @abstractmethod
    def check(self) -> list[T]:
        """Execute the monitor logic and return a list of alerts/results."""
        pass


class IntervalProjectMonitor(BaseMonitor[T]):
    """Standardized logic for tracking interval-based per-project checks."""

    def __init__(
        self,
        projects: Optional[dict[str, str]] = None,
        interval_seconds: int = 1800,
        engine: Any = None,
    ):
        self.projects = projects or {}
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _should_run(self, key: str, now: float) -> bool:
        """Determines if enough time has passed to run the check again."""
        last_run = self._last_runs.get(key, 0)
        return now - last_run >= self.interval_seconds

    def _mark_run(self, key: str, now: float) -> None:
        """Records the time a check was run."""
        self._last_runs[key] = now

    def generate_alerts(self, checkPathFunc) -> list[T]:
        """Orchestrate sweeps across all projects. checkPathFunc(project, path) -> T | None"""
        if not self.projects:
            return []

        alerts: list[T] = []
        now = time.monotonic()

        for project, path_str in self.projects.items():
            if not self._should_run(project, now):
                continue

            try:
                alert = checkPathFunc(project, path_str)
                if alert:
                    alerts.append(alert)
                self._mark_run(project, now)
            except (ValueError, OSError, RuntimeError) as e:
                logger.error("Monitor failed on %s: %s", project, e)

        return alerts
