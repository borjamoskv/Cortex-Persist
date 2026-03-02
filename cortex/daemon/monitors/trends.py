"""Google Trends Monitor."""

from __future__ import annotations

import logging
from typing import Any

from cortex.daemon.models import TrendsAlert
from cortex.daemon.monitors.base import BaseMonitor

logger = logging.getLogger("moskv-daemon")


class TrendsMonitor(BaseMonitor[TrendsAlert]):
    """Collects and reports real-time trends from the Trends Oracle."""

    def __init__(self, oracle: Any):
        """Initializes the monitor with a reference to the running Oracle."""
        self._oracle = oracle

    def check(self) -> list[TrendsAlert]:
        """Provides the pending alerts to the daemon."""
        if not self._oracle:
            return []

        try:
            # We fetch all alerts generated since the last cycle
            alerts = self._oracle.consume_alerts()
            return alerts
        except Exception as e:  # noqa: BLE001
            logger.error("TrendsMonitor check failed: %s", e)
            return []
