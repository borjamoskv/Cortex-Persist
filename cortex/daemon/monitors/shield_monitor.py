"""
CORTEX v8 — Daily Shield Monitor (Daemon).

Scheduled security pipeline that runs daily:
  04:00 → ThreatFeedEngine.update_daily()
  04:05 → IntegrityAuditor.full_audit()
  04:10 → AnomalyDetector.generate_daily_report()

Also provides on-demand scanning via the daemon API.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("moskv-daemon")

__all__ = ["DailyShieldMonitor"]


class DailyShieldMonitor:
    """Daily automated anti-hacker shield for the MOSKV daemon.

    Integrates: ThreatFeedEngine, IntegrityAuditor, AnomalyDetector.
    Runs on a schedule or on-demand via check_async().
    """

    SCAN_INTERVAL_HOURS: int = 24

    def __init__(self) -> None:
        self._last_scan: datetime | None = None
        self._last_report: dict[str, Any] = {}

    async def check_async(self) -> list[dict[str, Any]]:
        """Run the full daily shield pipeline.

        Returns list of alerts/findings.
        """
        alerts: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        # Skip if already ran within interval
        if self._last_scan:
            hours_since = (now - self._last_scan).total_seconds() / 3600
            if hours_since < self.SCAN_INTERVAL_HOURS:
                logger.debug(
                    "Shield scan skipped — last ran %.1fh ago",
                    hours_since,
                )
                return alerts

        logger.info("🛡️ DAILY SHIELD — Starting security pipeline")

        # ── Phase 1: Threat Feed Update ──
        feed_report = await self._update_feeds()
        if feed_report:
            alerts.append(
                {
                    "type": "threat_feed_update",
                    "severity": "info",
                    "details": feed_report,
                }
            )

        # ── Phase 2: Integrity Audit ──
        audit_report = await self._run_audit()
        if audit_report:
            severity = "info" if audit_report.get("is_clean") else "critical"
            alerts.append(
                {
                    "type": "integrity_audit",
                    "severity": severity,
                    "details": audit_report,
                }
            )
            if severity == "critical":
                await self._notify_threat(
                    "🔴 INTEGRITY VIOLATION DETECTED",
                    audit_report,
                )

        # ── Phase 3: Anomaly Report ──
        anomaly_stats = self._get_anomaly_stats()
        if anomaly_stats:
            alerts.append(
                {
                    "type": "anomaly_stats",
                    "severity": "info",
                    "details": anomaly_stats,
                }
            )

        self._last_scan = now
        self._last_report = {
            "timestamp": now.isoformat(),
            "alerts": len(alerts),
            "phases_completed": 3,
        }

        logger.info(
            "🛡️ DAILY SHIELD — Complete. %d alerts generated.",
            len(alerts),
        )
        return alerts

    def check(self) -> list[dict[str, Any]]:
        """Synchronous wrapper for check_async."""
        try:
            return asyncio.run(self.check_async())
        except RuntimeError:
            return []

    @property
    def last_report(self) -> dict[str, Any]:
        """Last scan report."""
        return self._last_report

    # ── Internal Methods ──

    async def _update_feeds(self) -> dict[str, Any] | None:
        """Update threat intelligence feeds."""
        try:
            from cortex.security.threat_feed import ThreatFeedEngine

            engine = ThreatFeedEngine()
            report = await engine.update_daily()
            return report.to_dict()
        except ImportError:
            logger.warning("ThreatFeedEngine not available")
        except Exception as e:  # noqa: BLE001
            logger.error("Threat feed update failed: %s", e)
        return None

    async def _run_audit(self) -> dict[str, Any] | None:
        """Run integrity audit."""
        try:
            from cortex.security.integrity_audit import IntegrityAuditor

            auditor = IntegrityAuditor()
            report = await auditor.full_audit()
            return report.to_dict()
        except ImportError:
            logger.warning("IntegrityAuditor not available")
        except Exception as e:  # noqa: BLE001
            logger.error("Integrity audit failed: %s", e)
        return None

    def _get_anomaly_stats(self) -> dict[str, Any] | None:
        """Get anomaly detection statistics."""
        try:
            from cortex.security.anomaly_detector import DETECTOR

            stats = DETECTOR.get_daily_stats()
            DETECTOR.reset_daily_stats()
            return stats
        except ImportError:
            return None

    async def _notify_threat(self, title: str, details: dict[str, Any]) -> None:
        """Send macOS notification for critical threats."""
        try:
            import subprocess

            msg = f"{title}: {details}"
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{msg}" with title "CORTEX Shield" sound name "Basso"',
                ],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass  # Notification is best-effort
