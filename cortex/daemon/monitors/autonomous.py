"""Autonomous MEJORAlo monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from cortex.daemon.models import MejoraloAlert

logger = logging.getLogger("moskv-daemon")


class AutonomousMejoraloMonitor:
    """Runs MEJORAlo scan automatically on configured projects."""

    projects: dict[str, str]
    interval_seconds: int

    def __init__(
        self,
        projects: dict[str, str] | None = None,
        interval_seconds: int = 1800,
        engine: Any = None,
    ):
        self.projects = projects or {}
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _check_project(
        self,
        project: str,
        path_str: str,
        now: float,
        mejoralo_engine_cls: Any,
    ) -> MejoraloAlert | None:
        """Helper to scan a single project and return an alert if successful."""
        last_run = self._last_runs.get(project, 0)
        if now - last_run < self.interval_seconds:
            return None

        path = Path(path_str).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return None

        try:
            m = mejoralo_engine_cls(engine=self._engine)
            logger.info("Autonomous MEJORAlo running on %s", project)
            result = m.scan(path)
            self._last_runs[project] = now
            return MejoraloAlert(
                project=project,
                score=result.score,
                dead_code=result.dead_code,
                total_loc=result.total_loc,
            )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("Autonomous MEJORAlo failed on %s: %s", project, e)

        return None

    def check(self) -> list[MejoraloAlert]:
        """Run MEJORAlo scan if interval has elapsed."""
        if not self.projects:
            return []

        alerts: list[MejoraloAlert] = []
        now = time.monotonic()

        try:
            from cortex.engine import CortexEngine  # noqa: F401
            from cortex.mejoralo import MejoraloEngine
        except ImportError:
            return []

        for project, path_str in self.projects.items():
            alert = self._check_project(project, path_str, now, MejoraloEngine)
            if alert:
                alerts.append(alert)

        return alerts
