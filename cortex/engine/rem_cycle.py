"""
CORTEX V7 — REM Coordinator (Deep Maintenance Cycle).

Orchestrates background tasks during low-activity phases (Sleep).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from cortex.engine.decalcifier import SovereignDecalcifier
from cortex.engine.growth import GROWTH_ENGINE
from cortex.engine.reaper import GhostReaper

logger = logging.getLogger("cortex.rem")


class REMCoordinator:
    """Manages system maintenance during the REM (Sleep) phase."""

    def __init__(self, db_conn: Any):
        self._conn = db_conn
        self._reaper = GhostReaper()
        self._decalcifier = SovereignDecalcifier()
        self._is_sleeping = False

    async def enter_rem(self) -> None:
        """Executes the deep maintenance cycle."""
        if self._is_sleeping:
            return

        from cortex.engine.evaporator import EntropicEvaporator

        self._is_sleeping = True
        logger.info("🌙 [REM] Entering Deep Sleep. Maintenance tasks starting.")

        evaporator = EntropicEvaporator(self._conn)

        tasks: list[Coroutine] = [
            self._reaper.reap_db_ghosts(self._conn),
            self._decalcifier.decalcify_cycle(self._conn),
            GROWTH_ENGINE.synaptic_pruning(self._conn),
            evaporator.evaporate(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error("❌ [REM] Task %d failed: %s", i, res)

        logger.info("🌅 [REM] Maintenance complete. System refreshed.")
        self._is_sleeping = False

    @property
    def is_active(self) -> bool:
        return self._is_sleeping
