"""
CORTEX v5.2 — Perception Layer 2: Metabolic Scaling.

Regulates the intensity of file system monitoring based on the
thermodynamic value (Exergy) of recent actions and the biological
significance (CrystalVitals) of the active project.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from cortex.extensions.perception.base import PERCEPTION_INTENSITY

logger = logging.getLogger("cortex.extensions.perception.metabolism")


class MetabolicObserver:
    """
    Dynamically adjusts the "heart rate" of the Perception Pipeline.

    Higher signal (meaningful diffs, high exergy) -> HIGH intensity.
    Lower signal (stale files, config changes) -> LOW intensity.
    """

    def __init__(self, initial_intensity: str = "MED") -> None:
        self.current_intensity = initial_intensity
        self._last_signal_time = time.monotonic()
        self._consecutive_low_exergy = 0

    def calculate_intensity(
        self,
        event_count: int,
        avg_diff_size: float,
        exergy_score: Optional[float] = None
    ) -> str:
        """
        Determine the target intensity based on activity and exergy.

        Args:
            event_count: Number of events in the current window.
            avg_diff_size: Average size (lines) of diffs in the window.
            exergy_score: Optional exergy score from the latest action.

        Returns:
            One of "LOW", "MED", "HIGH".
        """
        # 1. Base logic: Intensity scales with exergy if provided
        if exergy_score is not None:
            if exergy_score > 0.4:  # High signal breakthrough
                self._consecutive_low_exergy = 0
                return "HIGH"
            if exergy_score < 0.05:  # Low progress / noise
                self._consecutive_low_exergy += 1
            else:
                self._consecutive_low_exergy = 0

        # 2. Activity-based scaling (fallback or reinforcement)
        # If we have many meaningful diffs, stay at least at MED
        if event_count > 10 and avg_diff_size > 5:
            return "HIGH" if event_count > 25 else "MED"

        # 3. Decay to LOW if no signal for a while
        if self._consecutive_low_exergy > 3:
            return "LOW"

        # 4. Default to MED
        return "MED"

    def get_config(self, intensity: str) -> dict[str, float]:
        """Return the configuration for a given intensity level."""
        return PERCEPTION_INTENSITY.get(intensity, PERCEPTION_INTENSITY["MED"])
