"""Engine health check for MOSKV daemon."""

from __future__ import annotations

import os
from pathlib import Path

from cortex.daemon.models import CORTEX_DB, EngineHealthAlert


class EngineHealthCheck:
    """Checks CORTEX database integrity."""

    def __init__(self, db_path: Path = CORTEX_DB):
        self.db_path = db_path

    def check(self) -> list[EngineHealthAlert]:
        """Return alerts if CORTEX database is missing or unreadable."""
        alerts: list[EngineHealthAlert] = []

        if not self.db_path.exists():
            alerts.append(
                EngineHealthAlert(
                    issue="database_missing",
                    detail=f"{self.db_path} not found",
                )
            )
            return alerts

        if not os.access(self.db_path, os.R_OK):
            alerts.append(
                EngineHealthAlert(
                    issue="database_unreadable",
                    detail=f"No read permission on {self.db_path}",
                )
            )
            return alerts

        try:
            size = self.db_path.stat().st_size
            if size == 0:
                alerts.append(
                    EngineHealthAlert(
                        issue="database_empty",
                        detail="Database file is 0 bytes",
                    )
                )
        except OSError as e:
            alerts.append(
                EngineHealthAlert(
                    issue="database_stat_error",
                    detail=str(e),
                )
            )

        return alerts
