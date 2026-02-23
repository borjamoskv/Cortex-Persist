"""Ghost watcher for MOSKV daemon."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from cortex.daemon.models import AGENT_DIR, DEFAULT_STALE_HOURS, GhostAlert

logger = logging.getLogger("moskv-daemon")


class GhostWatcher:
    """Monitors ghosts.json and alerts on stale projects."""

    def __init__(
        self,
        ghosts_path=AGENT_DIR / "memory" / "ghosts.json",
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

        now = datetime.now(timezone.utc)
        stale: list[GhostAlert] = []

        for project, data in ghosts.items():
            try:
                ts = data.get("timestamp", "")
                if not ts:
                    continue
                # Skip ghosts that are intentionally blocked (parked)
                if data.get("blocked_by"):
                    continue
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
