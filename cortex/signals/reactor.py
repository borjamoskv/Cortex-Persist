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

from cortex.signals.bus import SignalBus

__all__ = ["SignalReactor"]

logger = logging.getLogger("cortex.signals.reactor")


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

    def process_once(self) -> int:
        """Poll the bus and execute one round of reflexes.

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
                self._dispatch(signal)
                processed += 1
            except Exception as e:
                logger.error(
                    "Reactor failed to process signal #%d (%s): %s",
                    signal.id,
                    signal.event_type,
                    e,
                    exc_info=True,
                )

        return processed

    def _dispatch(self, signal: Any) -> None:
        """Map signal types to reflex handlers."""
        etype = signal.event_type

        if etype == "compact:needed":
            self._handle_compact_needed(signal)
        elif etype == "fact:stored":
            self._handle_fact_stored(signal)
        elif etype == "experience:recorded":
            self._handle_experience_recorded(signal)
        else:
            logger.debug("Reactor ignored unknown signal type: %s", etype)

    def _handle_experience_recorded(self, signal: Any) -> None:
        """Reflex: Reconcile an experience into stratified memory layers."""
        if not self.engine or not self.engine.memory:
            logger.warning(
                "Experience reconciliation failed: Engine or MemoryManager not available."
            )
            return

        try:
            logger.info("Reactor: Reconciling experience signal #%d", signal.id)
            self._run_async(self.engine.memory.reconcile_experience(signal))
        except Exception as e:
            logger.error("Failed to reconcile experience reflex: %s", e)

    def _handle_compact_needed(self, signal: Any) -> None:
        """Reflex: Automate memory compaction."""
        project = signal.project or signal.payload.get("project")
        if not project:
            logger.warning("compact:needed signal missing project context.")
            return

        try:
            from cortex.compaction.compactor import compact

            logger.info("Reactor triggering autonomous compaction for [%s]", project)

            # compact is async, we need to run it in the loop
            result = self._run_async(compact(engine=self.engine, project=project, dry_run=False))

            if result:
                logger.info("Reflex: Compaction done for %s. -%d facts.", project, result.reduction)
        except Exception as e:
            logger.error("Failed to run compaction reflex: %s", e)

    def _handle_fact_stored(self, signal: Any) -> None:
        """Reflex: Regenerate snapshot (with cooldown)."""
        now = time.monotonic()
        if now - self._last_snapshot_time < self._snapshot_cooldown:
            return

        try:
            from cortex.sync import export_snapshot

            logger.info("Reactor triggering autonomous snapshot export.")
            self._run_async(export_snapshot(self.engine))

            self._last_snapshot_time = now
            logger.info("Reflex: Snapshot updated.")
        except Exception as e:
            logger.error("Failed to run snapshot reflex: %s", e)

    def _run_async(self, coro: Any) -> Any:
        """Helper to run async code from sync reactor context."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are in a thread with a running loop (like MoskvDaemon)
                # But compact() needs to be awaited.
                # For a reactor thread, we usually use a private loop or run_coroutine_threadsafe.
                # However, many of these are one-off.
                # If we are in the main thread of the daemon, we can't run_async.

                # Best approach for the daemon's architecture:
                # MoskvDaemon uses threading.Thread for these loops.
                # We can just create a new loop for each task if needed,
                # or use a shared one.

                # Given our current constraints:
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                return future.result()
            else:
                return asyncio.run(coro)
        except RuntimeError:
            return asyncio.run(coro)
        except Exception as e:
            logger.error("Async execution failed in reactor: %s", e)
            return None

    def run_loop(self, interval: float = 5.0) -> None:
        """Start a blocking infinite loop for standalone usage."""
        logger.info("Signal Reactor active — monitoring bus pulses (L2)")
        while True:
            try:
                count = self.process_once()
                if count > 0:
                    logger.debug("Reactor: Processed %d signal(s)", count)
            except Exception as e:
                logger.error("Reactor loop error: %s", e)

            time.sleep(interval)
