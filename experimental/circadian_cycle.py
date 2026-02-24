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
from typing import Callable, List


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
        self.sleep_tasks: List[Callable[[], None]] = []

    # ---------------------------------------------------------------------
    def is_sleeping(self, now: datetime.datetime | None = None) -> bool:
        """Return ``True`` if the current time falls inside the sleep window.

        Parameters
        ----------
        now: datetime, optional
            Allows injection of a custom timestamp for testing. If omitted the
            system local time is used.
        """
        now = now or datetime.datetime.now()
        hour = now.hour
        # Sleep window may wrap around midnight (e.g., 22‑06)
        if self.wake_hour < self.sleep_hour:
            return self.wake_hour <= hour < self.sleep_hour
        # Wrapped case
        return hour >= self.wake_hour or hour < self.sleep_hour

    # ---------------------------------------------------------------------
    def register_sleep_task(self, task: Callable[[], None]) -> None:
        """Add a callable that will be executed during the sleep phase.

        The task should be quick (seconds) because the sleep window may be
        short. Heavy‑weight jobs can be split into smaller chunks.
        """
        self.sleep_tasks.append(task)

    # ---------------------------------------------------------------------
    def run_sleep_cycle(self) -> None:
        """Execute all registered sleep tasks.

        This method is intended to be called by an external scheduler when the
        agent detects that it is in the sleep window. It simply iterates over the
        ``sleep_tasks`` list and calls each function, swallowing exceptions so
        that a failing task does not abort the whole cycle.
        """
        for task in self.sleep_tasks:
            try:
                task()
            except Exception as exc:  # pragma: no cover – defensive
                # In a real system you would log this.
                print(f"[CircadianCycle] Sleep task error: {exc}")

    # ---------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a serialisable representation of the current cycle state."""
        return {
            "wake_hour": self.wake_hour,
            "sleep_hour": self.sleep_hour,
            "is_sleeping": self.is_sleeping(),
            "registered_tasks": len(self.sleep_tasks),
        }

# Example usage (remove before production)
if __name__ == "__main__":
    cc = CircadianCycle()
    print(cc.snapshot())
```
