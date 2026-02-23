"""Autonomous Compaction monitor for MOSKV daemon (El Ciclo de Sueño)."""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.daemon.models import CompactionAlert

logger = logging.getLogger("moskv-daemon")


class CompactionMonitor:
    """Runs memory compaction automatically to fight context rot (24/7 Sleep Cycle)."""

    projects: list[str]
    interval_seconds: int

    def __init__(
        self,
        projects: list[str] | None = None,
        interval_seconds: int = 28800,  # 8 hours standard sleep cycle
        engine: Any = None,
    ):
        self.projects = projects or []
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _compact_project(
        self,
        project: str,
        now: float,
    ) -> CompactionAlert | None:
        """Helper to compact a single project's memory."""
        last_run = self._last_runs.get(project, 0)

        # Enforce the sleep cycle interval
        if now - last_run < self.interval_seconds:
            return None

        try:
            from cortex.compactor import compact

            logger.info("Autonomous Compaction (REM Sleep) running on %s", project)

            # Run the actual compaction directly using the injected engine
            result = compact(engine=self._engine, project=project, dry_run=False)
            self._last_runs[project] = now

            # We only alert if there was actual garbage collected
            if result.reduction > 0 or result.deprecated_ids:
                return CompactionAlert(
                    project=project,
                    reduction=result.reduction,
                    deprecated=len(result.deprecated_ids),
                    message=f"Sueño Reparador: {project} compactado. -{result.reduction} facts ruidosos eliminados.",
                )

            return None

        except (ValueError, OSError, RuntimeError, ImportError) as e:
            logger.error("Autonomous Compaction failed on %s: %s", project, e)
            return None

    def check(self) -> list[CompactionAlert]:
        """Run Compaction if interval has elapsed for registered projects."""
        if not self.projects or not self._engine:
            return []

        alerts: list[CompactionAlert] = []
        now = time.monotonic()

        for project in self.projects:
            alert = self._compact_project(project, now)
            if alert:
                alerts.append(alert)

        return alerts
