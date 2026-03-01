"""Moltbook heartbeat monitor — periodic social presence for MOSKV-1.

Runs the Moltbook heartbeat cycle at a configurable interval (default: 4 hours).
Handles rate limits gracefully and reports results as MoltbookAlert.
"""

from __future__ import annotations

import logging
import time

from cortex.daemon.models import MoltbookAlert

logger = logging.getLogger("moskv-daemon")

DEFAULT_MOLTBOOK_INTERVAL = 14400  # 4 hours


class MoltbookMonitor:
    """Periodic Moltbook heartbeat — social presence for MOSKV-1."""

    def __init__(self, interval_seconds: int = DEFAULT_MOLTBOOK_INTERVAL) -> None:
        self.interval_seconds = interval_seconds
        self._last_run: float = 0.0

    def check(self) -> list[MoltbookAlert]:
        """Run heartbeat if interval has elapsed."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        alerts: list[MoltbookAlert] = []
        try:
            from cortex.moltbook.heartbeat import MoltbookHeartbeat

            hb = MoltbookHeartbeat()
            summary = hb.run()

            actions = summary.get("actions", [])
            errors = summary.get("errors", [])
            karma = summary.get("home", {}).get("karma", 0)

            if errors:
                for err in errors:
                    logger.warning("🦞 Moltbook heartbeat error: %s", err)
                    alerts.append(
                        MoltbookAlert(
                            karma=karma,
                            actions_taken=actions,
                            message=f"Heartbeat error: {err}",
                            success=False,
                        )
                    )
            else:
                action_str = ", ".join(actions) if actions else "no activity"
                logger.info(
                    "🦞 Moltbook heartbeat OK — karma=%d, actions=[%s]",
                    karma,
                    action_str,
                )
                alerts.append(
                    MoltbookAlert(
                        karma=karma,
                        actions_taken=actions,
                        message=f"Heartbeat OK: {action_str}",
                        success=True,
                    )
                )

        except (ImportError, ValueError, OSError, RuntimeError) as e:
            logger.error("🦞 Moltbook monitor failed: %s", e)
            alerts.append(
                MoltbookAlert(
                    karma=0,
                    actions_taken=[],
                    message=f"Monitor error: {e}",
                    success=False,
                )
            )

        self._last_run = time.monotonic()
        return alerts
