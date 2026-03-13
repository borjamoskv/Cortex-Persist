"""AutoAudit monitor for the CORTEX daemon (Keter Layer)."""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

from cortex.daemon.models import AutoAuditAlert
from cortex.daemon.monitors.base import BaseMonitor

logger = logging.getLogger("moskv-daemon")


class AutoAuditMonitor(BaseMonitor[AutoAuditAlert]):
    """Periodically diagnoses system health and triggers Cognitive Layer."""

    def __init__(
        self,
        engine: Any = None,
        interval_seconds: int = 3600,
        ghost_threshold: int = 10,
        error_threshold: int = 50,
    ):
        self._engine = engine
        self._last_run = 0.0
        self.interval_seconds = interval_seconds
        self.ghost_threshold = ghost_threshold
        self.error_threshold = error_threshold

    def check(self) -> list[AutoAuditAlert]:
        """Aggregate system metrics and detect 'bleeding'."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        if not self._engine:
            return []

        alerts: list[AutoAuditAlert] = []
        try:
            # Gather db_path dynamically to support test vs prod environments
            db_path = getattr(self._engine, "db_path", None)
            if not db_path or not db_path.exists():
                return alerts

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                # Filter for active (not soft-deleted) facts
                cursor.execute(
                    "SELECT COUNT(*) FROM facts WHERE fact_type = 'ghost' AND valid_until IS NULL"
                )
                ghost_count = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM facts WHERE fact_type = 'error' AND valid_until IS NULL"
                )
                error_count = cursor.fetchone()[0]

                # Metric 3: Stagnation Detection (Ω₆)
                cursor.execute(
                    "SELECT COUNT(*) FROM facts WHERE created_at > datetime('now', '-24 hours')"
                )
                activity_24h = cursor.fetchone()[0]

                if ghost_count > self.ghost_threshold:
                    severity = "critical" if ghost_count > self.ghost_threshold * 2 else "high"
                    alerts.append(
                        AutoAuditAlert(
                            issue_type="high_ghosts",
                            severity=severity,
                            message=f"System is bleeding: {ghost_count} active ghosts detected.",
                            metrics={"ghost_count": ghost_count, "error_count": error_count},
                        )
                    )
                elif error_count > self.error_threshold:
                    alerts.append(
                        AutoAuditAlert(
                            issue_type="high_errors",
                            severity="medium",
                            message=f"System entropy rising: {error_count} active errors tracked.",
                            metrics={"ghost_count": ghost_count, "error_count": error_count},
                        )
                    )
                elif activity_24h == 0:
                    alerts.append(
                        AutoAuditAlert(
                            issue_type="stagnation",
                            severity="low",
                            message="Zero activity detected in 24h. System is entering stasis.",
                            metrics={"activity_24h": activity_24h},
                        )
                    )

            self._last_run = now
        except sqlite3.OperationalError as e:
            logger.debug("AutoAuditMonitor DB check skipped (table missing or locked): %s", e)
        except Exception as e:  # noqa: BLE001
            logger.error("AutoAuditMonitor failed: %s", e)

        return alerts
