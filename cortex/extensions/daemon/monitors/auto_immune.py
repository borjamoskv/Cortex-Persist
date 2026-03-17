"""Auto-Immune Monitor for MOSKV daemon.

Reads stale ghosts and dispatches them to the Aether Agent queue for autonomous resolution.
"""

from __future__ import annotations
from typing import Optional

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from cortex.extensions.daemon.models import AGENT_DIR, DEFAULT_STALE_HOURS
from cortex.extensions.daemon.monitors.base import BaseMonitor

try:
    from cortex.extensions.aether.models import AgentTask, TaskSource
    from cortex.extensions.aether.queue import TaskQueue

    _AETHER_AVAILABLE = True
except ImportError:
    _AETHER_AVAILABLE = False

logger = logging.getLogger("moskv-daemon")


class AutoImmuneMonitor(BaseMonitor):
    """Monitors ghosts.json and queues stale ghosts to Aether."""

    def __init__(
        self,
        queue: Optional[TaskQueue] = None,
        ghosts_path: Path = AGENT_DIR / "memory" / "ghosts.json",
        stale_hours: float = DEFAULT_STALE_HOURS,
    ):
        self.queue = queue
        self.ghosts_path = ghosts_path
        self.stale_hours = stale_hours

    def check(self) -> list[str]:
        """Dispatch stale ghosts to Aether queue. Returns list of queued task IDs."""
        if not _AETHER_AVAILABLE or not self.queue or not self.ghosts_path.exists():
            return []

        try:
            ghosts = json.loads(self.ghosts_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read ghosts.json: %s", e)
            return []

        now = datetime.now(timezone.utc)
        queued_ids: list[str] = []
        changes_made = False

        for project, data in ghosts.items():
            if self._should_dispatch(project, data, now):
                task_id = self._dispatch(project, data)
                if task_id:
                    queued_ids.append(task_id)
                    changes_made = True

        if changes_made:
            self._save_ghosts(ghosts)

        return queued_ids

    def _should_dispatch(self, project: str, data: dict, now: datetime) -> bool:
        """Determines if a ghost should be dispatched to Aether."""
        if not isinstance(data, dict):
            return False

        ts = data.get("timestamp", "")
        if not ts or data.get("blocked_by"):
            return False

        try:
            last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hours = (now - last).total_seconds() / 3600
            return hours > self.stale_hours
        except (ValueError, TypeError):
            return False

    def _dispatch(self, project: str, data: dict) -> Optional[str]:
        """Creates and enqueues an AgentTask for the ghost."""
        if not self.queue:
            return None

        mood = data.get("mood", "Stale anomaly detected.")
        ts = data.get("timestamp", "unknown")
        repo_path = data.get("repo_path", str(Path.home() / "cortex"))

        task = AgentTask(
            title=f"Auto-Immune: Resolve Ghost '{project}'",
            description=(
                f"Ghost resolution requested.\n\nProject: {project}\n"
                f"Details: {mood}\nLast Update: {ts}"
            ),
            repo_path=repo_path,
            source=TaskSource.GHOST,
        )
        self.queue.enqueue(task)
        logger.info("🛡️ Auto-Immune %s -> Aether (%s)", project, task.id)
        data["blocked_by"] = f"AETHER[{task.id}]"
        return task.id

    def _save_ghosts(self, ghosts: dict) -> None:
        try:
            self.ghosts_path.write_text(json.dumps(ghosts, indent=2, ensure_ascii=False))
        except OSError as e:
            logger.error("Failed to update ghosts.json: %s", e)
