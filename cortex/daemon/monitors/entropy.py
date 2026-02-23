"""Entropy monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from cortex.daemon.models import EntropyAlert

logger = logging.getLogger("moskv-daemon")


class EntropyMonitor:
    """Runs MEJORAlo scan and alerts when entropy exceeds threshold."""

    def __init__(
        self,
        projects: dict[str, str],
        interval_seconds: int = 1800,
        threshold: int = 90,
        engine: Any = None,
    ):
        self.projects = projects
        self.interval_seconds = interval_seconds
        self.threshold = threshold
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _check_project(
        self,
        project: str,
        path_str: str,
        now: float,
        mejoralo_engine_cls: Any,
    ) -> EntropyAlert | None:
        last_run = self._last_runs.get(project, 0)
        if now - last_run < self.interval_seconds:
            return None

        path = Path(path_str).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return None

        try:
            m = mejoralo_engine_cls(engine=self._engine)
            logger.debug("ENTROPY-0 scanner over %s", project)
            result = m.scan(path)
            self._last_runs[project] = now
            if result.score < self.threshold:
                return EntropyAlert(
                    project=project,
                    file_path=str(path),
                    complexity_score=result.score,
                    message=f"Entropía detectada: {result.score}/{self.threshold}",
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("ENTROPY-0 monitor failed on %s: %s", project, e)

        return None

    def check(self) -> list[EntropyAlert]:
        """Ejecuta escaneo de entropía y reporta si el score < threshold."""
        if not self.projects:
            return []

        alerts: list[EntropyAlert] = []
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
