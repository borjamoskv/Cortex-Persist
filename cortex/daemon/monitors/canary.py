"""Canary monitor for MOSKV daemon — Active HoneyPots."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cortex import config
from cortex.daemon.models import SecurityAlert
from cortex.database.core import connect_async

logger = logging.getLogger("moskv-daemon")

# List of files to watch. These are mentioned in the Sovereign Security Protocol.
CANARY_FILES = [
    Path("~/.cortex/canaries/secrets.env").expanduser(),
    Path("~/.cortex/canaries/aws_secrets.txt").expanduser(),
    Path("~/.aws/credentials_canary").expanduser(),
]


class CanaryMonitor:
    """Monitors activity on 'Active HoneyPots' (Canary Files).

    If any unauthorized process or user touches these files, a high-severity
    security alert is generated, triggering the lockdown protocol.
    """

    def __init__(self):
        self._last_stats: dict[Path, float] = {}
        self._ensure_canaries()

    def _ensure_canaries(self):
        """Ensure canary files exist to be monitored."""
        for path in CANARY_FILES:
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(
                    "# CORTEX SOVEREIGN CANARY\n"
                    "# DO NOT TOUCH. Unauthorized access triggers LOCKDOWN.\n"
                    f"STRIKE_KEY={os.urandom(16).hex()}\n",
                    encoding="utf-8",
                )
            # Initialize stats with current access/mod time
            try:
                st = path.stat()
                self._last_stats[path] = max(st.st_atime, st.st_mtime)
            except OSError:
                pass

    async def check_async(self) -> list[SecurityAlert]:
        """Check if any canary files have been accessed or modified."""
        alerts: list[SecurityAlert] = []
        for path in CANARY_FILES:
            try:
                if not path.exists():
                    logger.critical("🚨 CANARY DELETED: %s", path)
                    # Re-create it immediately
                    self._ensure_canaries()
                    current_val = 0.0  # Force alert
                else:
                    st = path.stat()
                    current_val = max(st.st_atime, st.st_mtime)

                last_val = self._last_stats.get(path, current_val)

                if current_val > last_val:
                    logger.critical("🔥 CANARY TRIPPED: Unauthorized access to %s", path)
                    alert = SecurityAlert(
                        ip_address="LOCAL_EXEC",
                        payload=f"Canary file touched/modified: {path}",
                        similarity_score=1.0,
                        confidence="C5",
                        summary="CANARY_TRIPPED: Active HoneyPot hit detected.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    alerts.append(alert)
                    self._last_stats[path] = current_val

                    # Persist to threat intel immediately
                    await self._trigger_lockdown(alert)

            except OSError as e:
                logger.error("Failed to stat canary %s: %s", path, e)

        return alerts

    async def _trigger_lockdown(self, alert: SecurityAlert) -> None:
        """Persist alert to DB to trigger global state change."""
        db_path = config.DB_PATH
        try:
            async with await connect_async(db_path) as conn:
                await conn.execute(
                    "INSERT INTO threat_intel (ip_address, reason, confidence) VALUES (?, ?, ?)",
                    (alert.ip_address, alert.summary, alert.confidence),
                )
                await conn.commit()
                logger.critical("🚨 KETER LOCKDOWN: System state escalated due to Canary hit.")
        except (sqlite3.Error, OSError):
            logger.error("Failed to commit lockdown state to DB")

    def check(self) -> list[SecurityAlert]:
        """Síncrono para el loop del daemon."""
        import asyncio

        try:
            return asyncio.run(self.check_async())
        except RuntimeError:
            return []
