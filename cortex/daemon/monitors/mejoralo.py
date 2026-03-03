"""
CORTEX v6.0 — OMEGA-SINGULARITY: Unified Project Quality Monitor.

Unifies AutonomousMejoraloMonitor and EntropyMonitor into a single,
zero-redundancy thermodynamic sweep. 

Resolves overlap detected in analyze_entropy.py (0.93 -> 0.0).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.daemon.models import EntropyAlert, MejoraloAlert
from cortex.daemon.monitors.base import IntervalProjectMonitor
from cortex.mejoralo import MejoraloEngine

logger = logging.getLogger("moskv-daemon")


class UnifiedMejoraloMonitor(IntervalProjectMonitor[Any]):
    """Sovereign monitor for project quality and entropy resolution."""

    def __init__(
        self,
        projects: dict[str, str] | None = None,
        interval_seconds: int = 1800,
        threshold: int = 90,
        engine: Any = None,
        auto_heal: bool = True,
    ):
        super().__init__(projects, interval_seconds, engine)
        self.threshold = threshold
        self.auto_heal = auto_heal
        self._stats = {"scans": 0, "heals": 0, "errors": 0}

    def _check_project(self, project: str, path_str: str) -> list[Any]:
        """Runs a single scan and returns both Mejoralo and/or Entropy alerts."""
        path = Path(path_str).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return []

        m = MejoraloEngine(engine=self._engine)
        logger.info("🌌 OMEGA-SINGULARITY sweep initiated for %s", project)

        # 1. Singular Scan
        result = m.scan(project, path, deep=True, brutal=True)
        self._stats["scans"] += 1
        
        initial_score = result.score
        alerts: list[Any] = []

        # 2. Entropy / Quality Violation Detection
        if initial_score < self.threshold and not result.dead_code:
            logger.warning(
                "🚨 Entropy breach in %s (score %d < %d).",
                project,
                initial_score,
                self.threshold,
            )
            
            # 3. Autonomous Healing (if enabled)
            if self.auto_heal:
                logger.info("🛠️  Triggering sovereign healing for %s...", project)
                if m.relentless_heal(project, path, result, target_score=100):
                    self._stats["heals"] += 1
                    # Full re-scan after heal
                    result = m.scan(project, path, deep=True)
                    logger.info(
                        "✅ Entropy resolved in %s. Score: %d -> %d",
                        project,
                        initial_score,
                        result.score,
                    )

        # 4. Generate Alerts (backward compatible with DaemonStatus)
        alerts.append(MejoraloAlert(
            project=project,
            score=result.score,
            dead_code=result.dead_code,
            total_loc=result.total_loc,
        ))

        if result.score < self.threshold:
            alerts.append(EntropyAlert(
                project=project,
                file_path=str(path),
                complexity_score=result.score,
                message=f"Persistent entropy: {result.score}/{self.threshold}",
            ))

        return alerts

    def check(self) -> list[Any]:
        """Orchestrate the unified sweep. Returns flattened list of alerts."""
        all_alerts: list[Any] = []
        nested = self.generate_alerts(self._check_project)
        for sublist in nested:
            if isinstance(sublist, list):
                all_alerts.extend(sublist)
        return all_alerts
