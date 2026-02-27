"""
CORTEX v8 — Security Visual Sync.

Bridge between the Security Layer and Notch Live (via WebSocket).
Translates security events into visual moods for the Notch CNS.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("cortex.security.sync")

__all__ = ["SecurityVisualSync", "SIGNAL"]


class SecurityVisualSync:
    """Synchronizes security states with the physical Notch visualizer."""

    MOODS = {
        "clean": "calm",  # Green-ish / Blue-ish
        "scanning": "thinking",  # Blue pulse
        "anomaly": "nervous",  # Yellow pulse
        "threat": "critical",  # Red pulse
        "pruning": "pruning",  # Entropy shockwave
    }

    def __init__(self) -> None:
        self._last_signal = None

    async def emit_signal(self, event_type: str, details: dict[str, Any] | None = None) -> None:
        """Send a visual signal to the Notch via NotchHub."""
        try:
            from cortex.routes.notch_ws import HUB

            mood = self.MOODS.get(event_type, "calm")

            # Construct the visual command for the Notch
            command = {
                "type": "mood",
                "value": mood,
                "intensity": details.get("intensity", 1.0) if details else 1.0,
                "details": details or {},
            }

            await HUB.broadcast(command)
            logger.debug("Visual signal [%s] broadcast to Notch", event_type)

        except ImportError:
            # HUB not available (e.g. running outside API context)
            pass
        except Exception as e:
            logger.error("Failed to emit security signal: %s", e)

    def emit_sync(self, event_type: str, details: dict[str, Any] | None = None) -> None:
        """Synchronous wrapper for emitting signals."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.emit_signal(event_type, details))
            else:
                loop.run_until_complete(self.emit_signal(event_type, details))
        except Exception:
            pass


# Global Singleton
SIGNAL = SecurityVisualSync()
