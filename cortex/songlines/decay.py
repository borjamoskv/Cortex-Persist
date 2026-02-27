"""
DecayEngine — The Radioactive Clock.
Calculates the semantic evaporation of ghost traces.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("cortex.songlines.decay")


class DecayEngine:
    """Taleb: Entropy Vigilance.

    Implements the radioactive decay formula to determine if a memory
    trace is still 'active' or has evaporated into background noise.
    """

    @staticmethod
    def calculate_resonance(created_at: float, half_life_hours: int) -> float:
        """Calculate current resonance strength [0.0, 1.0].

        Formula: N(t) = N0 * (0.5 ^ (t / T1/2))
        """
        now = datetime.now(timezone.utc).timestamp()
        age_seconds = now - created_at
        age_hours = age_seconds / 3600.0

        if age_hours < 0:
            return 1.0

        strength = 0.5 ** (age_hours / half_life_hours)
        return strength

    @staticmethod
    def is_expired(created_at: float, half_life_hours: int, threshold: float = 0.05) -> bool:
        """Check if the resonance has dropped below the visibility threshold."""
        return DecayEngine.calculate_resonance(created_at, half_life_hours) < threshold
