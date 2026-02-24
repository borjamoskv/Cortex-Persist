# zero_prompting.py
"""Zero‑Prompting module.

Implements a lightweight observer that watches user activity (e.g., idle time)
and proactively suggests actions when a friction threshold is exceeded. The
module is deliberately decoupled from any UI framework – it simply calls a
callback (`notify`) that the host application can wire to a notification system
(e.g., desktop toast, Slack message, or in‑app banner).

The core idea follows the *proactividad radical* principle from the design
specification: the agent does not wait for an explicit prompt but acts when it
detects that the user has been blocked for a configurable amount of time.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ZeroPrompting:
    """Detect friction and emit proactive suggestions.

    Parameters
    ----------
    idle_threshold_seconds: int
        Number of seconds of inactivity after which a suggestion is generated.
    notify: Callable[[str], None]
        Callback that receives the suggestion message. The host application decides
        how to present it to the user.
    """

    idle_threshold_seconds: int = 900  # 15 minutes by default
    notify: Callable[[str], None] = print
    _last_activity: float = field(default_factory=lambda: time.time(), init=False)

    # ---------------------------------------------------------------------
    def record_activity(self) -> None:
        """Call this whenever the user performs an action (e.g., a request)."""
        self._last_activity = time.time()

    # ---------------------------------------------------------------------
    def _idle_time(self) -> float:
        return time.time() - self._last_activity

    # ---------------------------------------------------------------------
    def check_and_prompt(self) -> None:
        """If idle time exceeds the threshold, emit a suggestion.

        The suggestion is phrased as a question to keep the interaction
        conversational, matching the *zero‑prompting* style.
        """
        idle = self._idle_time()
        if idle >= self.idle_threshold_seconds:
            minutes = int(idle // 60)
            message = (
                f"💡 He notado que llevas {minutes} min sin actividad. "
                "¿Te gustaría que prepare un script para automatizar la tarea que "
                "parece estar bloqueándote?"
            )
            self.notify(message)
            # Reset timer after notifying to avoid spamming
            self._last_activity = time.time()

    # ---------------------------------------------------------------------
    def start_background_loop(self, interval: int = 30) -> None:
        """Convenient helper for simple scripts – runs ``check_and_prompt``
        every *interval* seconds. In production you would run this in a separate
        thread or async task.
        """
        try:
            while True:
                self.check_and_prompt()
                time.sleep(interval)
        except KeyboardInterrupt:
            # Graceful exit when the host terminates the loop.
            pass

# Example usage (remove before packaging)
if __name__ == "__main__":
    zp = ZeroPrompting()
    # Simulate activity then a long idle period
    zp.record_activity()
    time.sleep(5)  # pretend user does something
    zp._last_activity -= 1000  # artificially create idle time
    zp.check_and_prompt()
```
