"""CORTEX — iMessage Sovereign Adapter.

Bridges CORTEX events to Messages.app via AppleScript.
Allows sending system alerts directly to your phone without external APIs.
"""

from __future__ import annotations
from typing import Optional

import asyncio
import logging
import sys

from cortex.extensions.notifications.adapters.base import BaseAdapter
from cortex.extensions.notifications.events import CortexEvent

logger = logging.getLogger("cortex.extensions.notifications.imessage")


class IMessageAdapter(BaseAdapter):
    """Sends CortexEvents via iMessage using local Messages.app."""

    name = "imessage"

    def __init__(self, target_phone_or_email: Optional[str] = None):
        super().__init__()
        self.target = target_phone_or_email

    @property
    def is_configured(self) -> bool:
        return sys.platform == "darwin" and self.target is not None

    async def send(self, event: CortexEvent) -> None:
        """Send an iMessage via osascript."""
        if not self.is_configured:
            return

        message = (
            f"{event.severity.emoji} *CORTEX: {event.title}*\n"
            f"[{event.source}]" + (f" @ {event.project}" if event.project else "") + "\n\n"
            f"{event.body}"
        )

        # Escape double quotes for AppleScript
        applescript_msg = message.replace('"', '\\"')

        script = f'''
        tell application "Messages"
            set targetBuddy to "{self.target}"
            set targetService to (1st service whose service type is iMessage)
            set theBuddy to buddy targetBuddy of targetService
            send "{applescript_msg}" to theBuddy
        end tell
        '''

        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.debug("iMessage sent to %s: %s", self.target, event.title)
            else:
                logger.error("iMessage failed (rc=%s): %s", proc.returncode, stderr.decode())
        except Exception as exc:  # noqa: BLE001
            logger.error("iMessage internal error: %s", exc)
