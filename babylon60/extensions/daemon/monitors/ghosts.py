# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from babylon60.extensions.daemon.models import AGENT_DIR, DEFAULT_STALE_HOURS, GhostAlert
from babylon60.extensions.daemon.monitors.base import BaseMonitor

logger = logging.getLogger("moskv-daemon")


class GhostWatcher(BaseMonitor[GhostAlert]):
    """Monitors ghosts.json and alerts on stale projects."""

    def __init__(
        self,
        ghosts_path: Path = AGENT_DIR / "memory" / "ghosts.json",
        stale_hours: float = DEFAULT_STALE_HOURS,
    ):
        self.ghosts_path = ghosts_path
        self.stale_hours = stale_hours

    def check(self) -> list[GhostAlert]:
        """Return list of projects that are stale."""
        if not self.ghosts_path.exists():
            return []

        try:
            ghosts = json.loads(self.ghosts_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read ghosts.json: %s", e)
            return []

        now = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        stale: list[GhostAlert] = []

        for project, data in ghosts.items():
            if not isinstance(data, dict):
                continue

            ts = data.get("timestamp", "")
            if not ts:
                continue
            # Skip ghosts that are intentionally blocked (parked)
            if data.get("blocked_by"):
                continue

            try:
                last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours = (now - last).total_seconds() / 3600
                if hours > self.stale_hours:
                    stale.append(
                        GhostAlert(
                            project=project,
                            last_activity=ts,
                            hours_stale=hours,
                            blocked_by=data.get("blocked_by", ""),
                            mood=data.get("mood", ""),
                        )
                    )
            except (ValueError, TypeError):
                continue

        return stale
