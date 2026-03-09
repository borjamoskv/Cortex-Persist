"""MOSKV-1 — PULSE-Ω (Sovereign Metabolism Engine).

Injects biological life into the CORTEX Daemon. Repurposed from the experimental
pulse.py script. Instead of static while-loops, the daemon's heart rate
fluctuates based on the actual system entropy and signal detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.daemon.metabolism")


@dataclass
class Vitals:
    """The OS's vital signs."""
    heart_rate: float = 1.0      # Execution frequency multiplier
    entropy: float = 0.0         # Accumulated noise/boredom
    signal: float = 1.0          # Useful state changes (alerts)
    age: int = 0                 # Total daemon loops


class MetabolismEngine:
    """
    Regulates the MOSKV-1 Daemon sleep cycle dynamically.
    High signal (alerts exist) -> Tachycardia -> Fast polling.
    Zero signal (peace) -> Bradycardia -> Slow polling to save CPU.
    """

    def __init__(self, base_interval: int = 60, min_interval: int = 5, max_interval: int = 600):
        self.vitals = Vitals()
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval

    @property
    def bpm(self) -> str:
        """Human-readable rhythm."""
        hr = self.vitals.heart_rate
        if hr > 1.8:
            return "🫀 TACHYCARDIA"
        if hr > 0.8:
            return "💚 NORMAL"
        if hr > 0.3:
            return "💛 BRADYCARDIA"
        return "🔵 HIBERNATION"

    def metabolize(self, total_alerts: int) -> float:
        """
        Feed the metabolism the result of the daemon check.
        Returns the number of seconds the daemon should sleep.
        """
        self.vitals.age += 1

        # ── Signal Detection ──
        if total_alerts > 0:
            # System is under stress or needs attention -> HIGH SIGNAL
            self.vitals.signal = min(2.0, self.vitals.signal + 0.3)
            self.vitals.entropy = max(0.0, self.vitals.entropy - 0.2)
        else:
            # Nothing happening -> High Entropy (boredom)
            self.vitals.signal = max(0.1, self.vitals.signal - 0.1)
            self.vitals.entropy += 0.1

        # ── Heart Rate Adjustment ──
        # Formula: Heart rate scales directly with signal, inversely to entropy.
        self.vitals.heart_rate = max(0.1, self.vitals.signal - (self.vitals.entropy * 0.05))

        # ── Wait Time Calculation ──
        # Higher heart rate = shorter sleep time
        wait_time = self.base_interval / self.vitals.heart_rate

        # Clamp to physical limits
        final_wait = max(self.min_interval, min(self.max_interval, wait_time))

        logger.info(
            "PULSE-Ω: %s [HR: %.2f | Sig: %.2f | Ent: %.2f] -> Next beat in %.0fs",
            self.bpm, self.vitals.heart_rate, self.vitals.signal, self.vitals.entropy, final_wait
        )
        return final_wait
