# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Signal monitor for MOSKV daemon.

Polls the L1 Signal Bus and executes L2 reflexes via SignalReactor.
Converts reactor events into Daemon Alerts.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from cortex.daemon.models import SignalAlert
from cortex.database.core import connect as db_connect

logger = logging.getLogger("moskv-daemon")


class SignalMonitor:
    """Watchdog for the Signal Bus — the L2 Reactor heart."""

    def __init__(self, db_path: str, engine: Any = None):
        self.db_path = db_path
        self._engine = engine
        self._reactor = None
        self._bus_conn = None

    def _ensure_reactor(self):
        if self._reactor:
            return

        try:
            from cortex.signals.bus import SignalBus
            from cortex.signals.reactor import SignalReactor

            # Standard sqlite3 connection for the bus
            self._bus_conn = db_connect(self.db_path)
            self._bus_conn.execute("PRAGMA journal_mode=WAL")

            bus = SignalBus(self._bus_conn)
            self._reactor = SignalReactor(bus, engine=self._engine)
            logger.info("SignalMonitor initialized L2 Reactor.")
        except (sqlite3.Error, ImportError) as e:
            logger.error("Failed to initialize SignalReactor: %s", e)

    def check(self) -> list[SignalAlert]:
        """Poll signals and process reflexes."""
        self._ensure_reactor()
        if not self._reactor:
            return []

        alerts: list[SignalAlert] = []
        try:
            # We process signals. The reactor itself logs its actions.
            # We wrap the reactor to capture what it did as alerts.

            # Since SignalReactor.process_once() returns a count,
            # we might want to extend it to return a list of actions.
            # For now, we'll poll the bus ourselves or just trust the reactor logs.

            # Improvement: The reactor could have a callback for alerts.
            # But let's keep it simple: the reactor processes them.
            # If we want them in the daemon status, we should return them here.

            # Let's peek at what we are about to process to generate alerts.
            signals_to_process = self._reactor.bus.peek(consumer="reactor", limit=20)

            count = self._reactor.process_once()

            if count > 0:
                for sig in signals_to_process[:count]:
                    alerts.append(
                        SignalAlert(
                            event_type=sig.event_type,
                            project=sig.project,
                            payload=sig.payload,
                            message=f"Reflex executed for {sig.event_type}",
                        )
                    )
        except Exception as e:
            logger.error("SignalMonitor check failed: %s", e)

        return alerts

    def shutdown(self):
        if self._bus_conn:
            self._bus_conn.close()
