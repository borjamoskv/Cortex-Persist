"""Memory syncer monitor for MOSKV daemon."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from cortex.daemon.models import AGENT_DIR, DEFAULT_MEMORY_STALE_HOURS, MemoryAlert

logger = logging.getLogger("moskv-daemon")


class MemorySyncer:
    """Alerts when system.json memory is stale."""

    def __init__(
        self,
        system_path=AGENT_DIR / "memory" / "system.json",
        stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
    ):
        self.system_path = system_path
        self.stale_hours = stale_hours

    def check(self) -> list[MemoryAlert]:
        """Return alerts for stale memory files."""
        if not self.system_path.exists():
            return []

        alerts: list[MemoryAlert] = []
        try:
            data = json.loads(self.system_path.read_text())
            ts = data.get("meta", {}).get("last_updated", "")
            if not ts:
                return []
            last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours = (now - last).total_seconds() / 3600
            if hours > self.stale_hours:
                alerts.append(
                    MemoryAlert(
                        file="system.json",
                        last_updated=ts,
                        hours_stale=hours,
                    )
                )
        except (OSError, ValueError) as e:
            logger.error("Failed to check system.json: %s", e)

        return alerts
