"""Health monitoring loop for moskv-daemon.

Uses sealed Grade enum for comparisons. TrendDetector for drift.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from cortex.extensions.health.collector import HealthCollector
from cortex.extensions.health.models import Grade
from cortex.extensions.health.scorer import HealthScorer
from cortex.extensions.health.trend import TrendDetector

logger = logging.getLogger("moskv-daemon.health")

DEFAULT_INTERVAL = 300
ALERT_COOLDOWN = 1800
DEGRADE_THRESHOLD = Grade.GOOD  # Alert below Good


class HealthLoop:
    """Daemon loop: autonomous health monitoring.

    Grade transitions use sealed enum comparison.
    TrendDetector tracks drift over time.
    """

    def __init__(
        self,
        db_path: str | Path = "",
        interval: float = DEFAULT_INTERVAL,
        notify_fn: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._db_path = str(db_path)
        self._interval = interval
        self._notify_fn = notify_fn
        self._last_grade: Optional[Grade] = None
        self._last_alert: float = 0.0
        self._trend = TrendDetector()

    def tick(self) -> Optional[dict]:
        """Run one health check cycle."""
        try:
            collector = HealthCollector(db_path=self._db_path)
            metrics = collector.collect_all()
            hs = HealthScorer.score(metrics)
            summary = HealthScorer.summarize(hs)

            self._trend.push(hs.score)
            drift = self._trend.detect_drift()

            logger.info(
                "Health tick: %s [trend=%s]",
                summary,
                drift,
            )

            # Grade change detection via enum comparison
            if self._last_grade is not None and hs.grade != self._last_grade:
                self._on_grade_change(
                    self._last_grade,
                    hs.grade,
                    hs.score,
                )

            # Alert on degradation
            if hs.grade < DEGRADE_THRESHOLD:
                self._alert_degraded(hs.score, hs.grade)

            self._last_grade = hs.grade

            return {
                "score": round(hs.score, 2),
                "grade": hs.grade.letter,
                "healthy": hs.healthy,
                "trend": drift,
                "slope": round(self._trend.slope(), 3),
                "metrics": [{"name": m.name, "value": m.value} for m in metrics],
            }

        except Exception as e:  # noqa: BLE001
            logger.warning("Health tick failed: %s", e)
            return None

    def _on_grade_change(
        self,
        old: Grade,
        new: Grade,
        score: float,
    ) -> None:
        """Handle grade transitions via enum ordering."""
        if new < old:
            logger.warning(
                "Health DEGRADED: %s → %s (%.1f)",
                old.letter,
                new.letter,
                score,
            )
            self._send_notification(
                f"⚠️ CORTEX Health: {old.letter} → {new.letter} ({score:.0f}/100)",
                "Health degradation detected.",
            )
        else:
            logger.info(
                "Health IMPROVED: %s → %s (%.1f)",
                old.letter,
                new.letter,
                score,
            )

    def _alert_degraded(
        self,
        score: float,
        grade: Grade,
    ) -> None:
        """Alert on sustained degradation (rate-limited)."""
        now = time.monotonic()
        if now - self._last_alert < ALERT_COOLDOWN:
            return
        self._last_alert = now
        self._send_notification(
            f"🔴 CORTEX Health: {score:.0f}/100 ({grade.letter})",
            "System health is below threshold.",
        )

    def _send_notification(
        self,
        title: str,
        body: str,
    ) -> None:
        """Dispatch notification via callback or macOS."""
        if self._notify_fn:
            try:
                self._notify_fn(title, body)
            except Exception as e:  # noqa: BLE001
                logger.debug("Notification failed: %s", e)
            return
        try:
            import subprocess

            subprocess.run(
                ["osascript", "-e", f'display notification "{body}" with title "{title}"'],
                check=False,
                capture_output=True,
            )
        except Exception:  # noqa: BLE001
            logger.debug("macOS notifications unavailable")

    def persist_snapshot(
        self,
        engine: object,
        data: dict,
    ) -> None:
        """Persist health snapshot as a CORTEX fact."""
        try:
            engine.store_sync(  # type: ignore[attr-defined]
                "cortex",
                content=(f"Health snapshot: {data['score']}/100 ({data['grade']})"),
                fact_type="bridge",
                source="daemon:health",
                tags=["health", "snapshot", data["grade"]],
                meta=data,
                confidence="C5",
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("Health persist failed: %s", e)
