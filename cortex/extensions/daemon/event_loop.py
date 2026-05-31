import asyncio
import signal
import threading
import time
import logging
from datetime import datetime, timezone
from cortex.extensions.daemon.models import DEFAULT_INTERVAL

logger = logging.getLogger("moskv-daemon")

class EventLoopMixin:

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
            """Run the daemon using the sovereign async loop (all subsystems as tasks)."""
            from cortex.events.loop import sovereign_run

            logger.info("🚀 MOSKV-1 Daemon starting in sovereign async mode (interval=%ds)", interval)
            sovereign_run(self.run_sovereign(interval=interval))

    def _signal_shutdown(self) -> None:
            """Signal handler for async loop."""

            logger.info("Received shutdown signal")

            self._shutdown = True

            self._stop_event.set()

            # Cancel all running tasks

            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()

    def _register_default_schedules(self) -> None:
            """Register built-in recurring tasks with the scheduler."""

            if self.scheduler is None:
                return

            # Hot state TTL purge every 10 minutes

            if self.hot_state is not None:
                self.scheduler.add_recurring(
                    "purge_expired_state",
                    lambda: asyncio.coroutine(lambda: self.hot_state.purge_expired())(),  # type: ignore
                    interval_s=600,
                    priority=8,
                )

