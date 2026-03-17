# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Signal Reactor (L2 Consciousness).

The Reactor listens for signals on the bus and triggers autonomous actions
(reflexes). It converts 'Events' into 'Work'.

Active Reflexes:
- compact:needed -> Triggers CompactionStrategy suite.
- fact:stored -> Triggers snapshot export (with cooldown).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.extensions.signals.bus import SignalBus
from cortex.utils.respiration import breathe, oxygenate

__all__ = ["SignalReactor"]

logger = logging.getLogger("cortex.extensions.signals.reactor")


class SignalReactor:
    """Reactive loop that transforms L1 pulses into L2 actions.

    Designed to be run as part of the MoskvDaemon or as a standalone
    CLI 'reactor' process.
    """

    def __init__(self, bus: SignalBus, engine: Any = None):
        self.bus = bus
        self.engine = engine
        self._last_snapshot_time: float = 0
        self._snapshot_cooldown: int = 60  # seconds

    @oxygenate(min_interval=0.1)
    async def process_once(self) -> int:
        """Poll the bus and execute one round of reflexes (oxygenated).

        Returns:
           The number of signals processed.
        """
        # We poll as 'reactor' consumer
        signals = self.bus.poll(consumer="reactor", limit=20)
        if not signals:
            return 0

        processed = 0
        for signal in signals:
            try:
                await self._dispatch(signal)
                processed += 1
                # Small breath between signals to avoid flooding the loop
                await breathe(0.01)
            except (ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.exception(
                    "Reactor failed to process signal #%d (%s): %s",
                    signal.id,
                    signal.event_type,
                    e,
                )

        return processed

    async def _dispatch(self, signal: Any) -> None:
        """Map signal types to reflex handlers."""
        etype = signal.event_type

        if etype == "compact:needed":
            await self._handle_compact_needed(signal)
        elif etype == "fact:stored":
            await self._handle_fact_stored(signal)
        elif etype == "experience:recorded":
            await self._handle_experience_recorded(signal)
        else:
            logger.debug("Reactor ignored unknown signal type: %s", etype)

    async def _handle_experience_recorded(self, signal: Any) -> None:
        """Reflex: Reconcile an experience into stratified memory layers."""
        if not self.engine or not self.engine.memory:
            logger.warning(
                "Experience reconciliation failed: Engine or MemoryManager not available."
            )
            return

        try:
            logger.info("Reactor: Reconciling experience signal #%d", signal.id)
            await self.engine.memory.reconcile_experience(signal)
        except (RuntimeError, OSError, AttributeError) as e:
            logger.exception("Failed to reconcile experience reflex: %s", e)

    async def _handle_compact_needed(self, signal: Any) -> None:
        """Reflex: Automate memory compaction."""
        project = signal.project or signal.payload.get("project")
        if not project:
            logger.warning("compact:needed signal missing project context.")
            return

        try:
            from cortex.compaction.compactor import compact

            logger.info("Reactor triggering autonomous compaction for [%s]", project)

            # compact is already async
            result = await compact(engine=self.engine, project=project, dry_run=False)

            if result:
                logger.info("Reflex: Compaction done for %s. -%d facts.", project, result.reduction)
        except (ImportError, RuntimeError, OSError) as e:
            logger.exception("Failed to run compaction reflex: %s", e)

    async def _handle_fact_stored(self, signal: Any) -> None:
        """Reflex: Regenerate snapshot (with cooldown)."""
        now = time.monotonic()
        if now - self._last_snapshot_time < self._snapshot_cooldown:
            return

        try:
            from cortex.extensions.sync import export_snapshot

            logger.info("Reactor triggering autonomous snapshot export.")
            await export_snapshot(self.engine)

            self._last_snapshot_time = now
            logger.info("Reflex: Snapshot updated.")
        except (ImportError, RuntimeError, OSError) as e:
            logger.exception("Failed to run snapshot reflex: %s", e)

    async def run_loop(self, interval: float = 5.0) -> None:
        """Start a non-blocking infinite loop for standalone usage. (PULMONES)"""
        logger.info("Signal Reactor active — monitoring bus pulses (L2) [OXYGENATED]")
        while True:
            try:
                count = await self.process_once()
                if count > 0:
                    logger.debug("Reactor: Processed %d signal(s)", count)
            except (RuntimeError, OSError, ValueError) as e:
                logger.exception("Reactor loop error: %s", e)

            await breathe(interval)
