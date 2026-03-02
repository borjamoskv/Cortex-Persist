"""Entropy monitor for MOSKV daemon."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.daemon.models import EntropyAlert
from cortex.daemon.monitors.base import IntervalProjectMonitor
from cortex.mejoralo import MejoraloEngine

logger = logging.getLogger("moskv-daemon")


class EntropyMonitor(IntervalProjectMonitor[EntropyAlert]):
    """Runs MEJORAlo scan and alerts when entropy exceeds threshold."""

    def __init__(
        self,
        projects: dict[str, str] | None = None,
        interval_seconds: int = 1800,
        threshold: int = 90,
        engine: Any = None,
    ):
        super().__init__(projects, interval_seconds, engine)
        self.threshold = threshold

    def _check_project(self, project: str, path_str: str) -> EntropyAlert | None:
        path = Path(path_str).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return None

        m = MejoraloEngine(engine=self._engine)
        logger.debug("ENTROPY-0 scanner over %s", project)

        result = m.scan(project, path)

        initial_score = result.score
        if initial_score < self.threshold and not result.dead_code:
            logger.warning(
                "Entropía CRÍTICA detectada en %s (score %d < %d). INICIANDO PURGA...",
                project,
                initial_score,
                self.threshold,
            )
            if m.relentless_heal(project, path, result, target_score=95):
                # Re-escaneo tras curación
                result = m.scan(project, path)
                logger.info(
                    "✅ Purga de Entropía completada en %s. Score: %d -> %d",
                    project,
                    initial_score,
                    result.score,
                )

        if result.score < self.threshold:
            return EntropyAlert(
                project=project,
                file_path=str(path),
                complexity_score=result.score,
                message=f"Entropía residual detectada: {result.score}/{self.threshold}",
            )

        return None

    def check(self) -> list[EntropyAlert]:
        """Ejecuta escaneo de entropía y reporta si el score < threshold."""
        return self.generate_alerts(self._check_project)
