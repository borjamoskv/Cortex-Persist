"""Autonomous MEJORAlo monitor for MOSKV daemon."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.daemon.models import MejoraloAlert
from cortex.daemon.monitors.base import IntervalProjectMonitor
from cortex.mejoralo import MejoraloEngine

logger = logging.getLogger("moskv-daemon")


class AutonomousMejoraloMonitor(IntervalProjectMonitor[MejoraloAlert]):
    """Runs MEJORAlo scan automatically on configured projects."""

    def __init__(
        self,
        projects: dict[str, str] | None = None,
        interval_seconds: int = 1800,
        engine: Any = None,
        auto_heal_threshold: int | None = 90,
    ):
        super().__init__(projects, interval_seconds, engine)
        self.auto_heal_threshold = auto_heal_threshold
        self._stats = {"scans": 0, "heals": 0, "errors": 0}

    def _check_project(self, project: str, path_str: str) -> MejoraloAlert | None:
        """Scan a project and trigger relentless healing if quality degrades."""
        path = Path(path_str).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return None

        m = MejoraloEngine(engine=self._engine)
        logger.info("🐝 Autonomous scan sequence inició for %s", project)

        result = m.scan(project, path, deep=True, brutal=True)
        self._stats["scans"] += 1

        initial_score = result.score

        # 2. Heurística de Auto-Curación (Sovereignty)
        threshold = self.auto_heal_threshold or 70
        if initial_score < threshold and not result.dead_code:
            logger.warning(
                "🚨 Quality Breach: %s score %d < %d. Triggering heal...",
                project,
                initial_score,
                threshold,
            )
            if m.relentless_heal(project, path, result, target_score=100):
                self._stats["heals"] += 1
                # Full re-scan after heal to update the alert
                result = m.scan(project, path, deep=True)
                logger.info(
                    "✅ Auto-curación completed for %s. Score: %d -> %d",
                    project,
                    initial_score,
                    result.score,
                )

        return MejoraloAlert(
            project=project,
            score=result.score,
            dead_code=result.dead_code,
            total_loc=result.total_loc,
        )

    def check(self) -> list[MejoraloAlert]:
        """Orchestrate the sovereign quality sweep across all projects."""
        return self.generate_alerts(self._check_project)
