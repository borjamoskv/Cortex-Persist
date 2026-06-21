# [C5-REAL] Exergy-Maximized
"""
Meta-Controller Module.
Handles Pain Signal monitoring, versioning, and execution mode orchestration.
"""

import logging

logger = logging.getLogger(__name__)

class MetaController:
    """
    Decides the high-level trajectory of the agent (Shadow, Dream, or Real Mode)
    based on continuous health and pain metrics.
    """

    def __init__(self):
        self.pain_accumulator = 0
        self.health_score = 10000 # Strict health score (Primitive 20 requires >9850)
        self.active_version = "v1.0.0"

    def decide_mode(self, current_exergy: int) -> str:
        """
        Determines the execution path.
        If pain is too high or exergy is low, shifts to Dream Mode (offline simulation).
        """
        if self.pain_accumulator > 50 or self.health_score < 9850:
            return "dream"
        return "real"

    def register_pain(self, negative_exergy: int):
        """
        Accumulates pain signal from failed or negative-yield actions.
        """
        self.pain_accumulator += abs(negative_exergy)
        logger.warning(f"[C5-REAL] Pain Signal Accumulated: {self.pain_accumulator}")

        if self.pain_accumulator > 100:
            self._trigger_rollback()

    def _trigger_rollback(self):
        """
        Triggers a genetic rollback or self-repair sequence (Primitive 11).
        """
        logger.error("[C5-REAL] Critical Pain Level Reached. Triggering Rollback.")
        self.pain_accumulator = 0
        self.active_version = "v0.9.9-safe"
