"""CORTEX — macOS Notification Adapter.

Delivers events as native macOS notifications via `osascript`.
Zero dependencies — uses stdlib subprocess only.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from cortex.notifications.adapters.base import BaseAdapter
from cortex.notifications.events import CortexEvent

logger = logging.getLogger("cortex.notifications.macos")


class MacOSAdapter(BaseAdapter):
    """Sends CortexEvents as native macOS notifications."""

    name = "macos"

    @property
    def is_configured(self) -> bool:
        return sys.platform == "darwin"

    async def send(self, event: CortexEvent) -> None:
        """Fire a macOS notification via osascript."""
        if not self.is_configured:
            return

        title = f"{event.severity.emoji} {event.title}"
        subtitle = f"[{event.source}]" + (f" · {event.project}" if event.project else "")
        body = event.body[:200]  # macOS truncates long notifications

        script = (
            f'display notification "{body}" '
            f'with title "{title}" '
            f'subtitle "{subtitle}" '
            f'sound name "Purr"'
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            logger.debug("macOS notification sent: %s", event.title)
        except OSError as exc:
            logger.error("macOS notification failed: %s", exc)
