"""V8 Governance: Evaluation Monitor."""

from __future__ import annotations
from typing import Union

import logging
import time
from pathlib import Path

from cortex.extensions.daemon.models import EvaluationAlert

logger = logging.getLogger("moskv-daemon")


class EvaluationMonitor:
    """Evaluates memory staleness and contradictions in the background.

    Part of CORTEX v8 Axis 1: Evaluation Layer.
    """

    def __init__(
        self,
        db_path: Union[Path, str],
        interval_seconds: int = 43200,  # 12 hours
    ):
        self.db_path = Path(db_path)
        self.interval_seconds = interval_seconds
        self._last_run: float = 0

    def check(self) -> list[EvaluationAlert]:
        """Run evaluation metrics."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        if not self.db_path.exists():
            return []

        self._last_run = now

        try:
            from cortex.database.core import connect as db_connect

            alerts = []
            with db_connect(self.db_path) as conn:  # type: ignore[type-error]
                cur = conn.cursor()
                import sqlite3

                try:
                    # Total facts
                    cur.execute("SELECT COUNT(*) FROM facts_meta")
                    total_row = cur.fetchone()
                    total = total_row[0] if total_row else 0

                    # Stale facts (> 180 days without subjective hit)
                    cur.execute(
                        "SELECT COUNT(*) FROM facts_meta WHERE last_accessed < datetime('now', '-180 days')"
                    )
                    stale_row = cur.fetchone()
                    stale_count = stale_row[0] if stale_row else 0

                    stale_ratio = (stale_count / total) if total > 0 else 0.0
                except sqlite3.OperationalError as e:
                    if "no such table: facts_meta" in str(e):
                        # L2 sqlite-vec is not fully active yet
                        total = 0
                        stale_count = 0
                        stale_ratio = 0.0
                    else:
                        raise

            # Heuristics Contradiction flag (0 for now, logic deferred to asynchronous batch LLM evaluation)
            contradictions = 0

            alerts.append(
                EvaluationAlert(
                    stale_ratio=stale_ratio,
                    stale_count=stale_count,
                    contradictions_found=contradictions,
                    message=(f"V8 Evaluation complete. Stale memory ratio: {stale_ratio:.2%}"),
                )
            )
            return alerts

        except Exception as e:  # noqa: BLE001
            logger.error("EvaluationMonitor error: %s", e)
            return []
