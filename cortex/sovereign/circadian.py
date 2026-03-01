# circadian_cycle.py
"""Circadian Cycle module for the synthetic agent.

Implements a simple day/night cycle that toggles between an *active* phase
(where the agent processes user requests) and a *sleep* phase (where it performs
background maintenance such as synaptic pruning, insight synthesis, and
compression of the internal memory).

The implementation is deliberately lightweight and uses the system clock to
determine the current phase. In production you could replace the time‑based
logic with a configurable schedule or an external trigger.
"""

from __future__ import annotations

import datetime
import inspect
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class CircadianCycle:
    """Manage active and sleep phases for the agent.

    The cycle assumes a 24‑hour period with configurable *wake* and *sleep*
    hour ranges. During the sleep phase the ``sleep_tasks`` callbacks are
    executed sequentially. Callbacks can be any coroutine or regular function
    that performs maintenance (e.g., pruning, summarisation).
    """

    def __init__(self, wake_hour: int = 6, sleep_hour: int = 22) -> None:
        if not (0 <= wake_hour < 24 and 0 <= sleep_hour < 24):
            raise ValueError("Hours must be in 0‑23 range")
        self.wake_hour = wake_hour
        self.sleep_hour = sleep_hour
        # Support both sync and async tasks
        self.sleep_tasks: list[Callable[[], Any]] = []

    # ---------------------------------------------------------------------
    def is_sleeping(self, now: datetime.datetime | None = None) -> bool:
        """Return ``True`` if the current time falls inside the sleep window."""
        now = now or datetime.datetime.now()
        hour = now.hour
        # Sleep window may wrap around midnight (e.g., 22‑06)
        if self.wake_hour < self.sleep_hour:
            # Wake at 6, Sleep at 22 -> Sleeping if hour >= 22 OR hour < 6
            return hour >= self.sleep_hour or hour < self.wake_hour
        # Wrapped case (e.g., Wake at 22, Sleep at 6) -> Sleeping if 6 <= hour < 22
        return self.sleep_hour <= hour < self.wake_hour

    # ---------------------------------------------------------------------
    def register_sleep_task(self, task: Callable[[], Any]) -> None:
        """Add a callable that will be executed during the sleep phase."""
        self.sleep_tasks.append(task)

    # ---------------------------------------------------------------------
    async def run_sleep_cycle(self) -> None:
        """Execute all registered sleep tasks asynchronously."""
        logger.info(
            "🌙 Entering REM Phase. Executing %d tasks.",
            len(self.sleep_tasks),
        )
        for task in self.sleep_tasks:
            try:
                if inspect.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except (OSError, RuntimeError, ValueError) as exc:
                logger.error("[CircadianCycle] Sleep task error: %s", exc)

    # ---------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a serialisable representation of the current cycle state."""
        return {
            "wake_hour": self.wake_hour,
            "sleep_hour": self.sleep_hour,
            "is_sleeping": self.is_sleeping(),
            "registered_tasks": len(self.sleep_tasks),
            "phase": "REM" if self.is_sleeping() else "ACTIVE"
        }


# Example usage (remove before production)
if __name__ == "__main__":
    # Configure basic logging for example usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    cc = CircadianCycle()
    print(cc.snapshot())
