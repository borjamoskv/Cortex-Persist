"""CORTEX Daemon — Maxwell's Performance Engine.

This background daemon drops low-exergy output from agents on the
fly if the Shannon Entropy density is low relative to payload size.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from cortex.engine.refinement import SovereignRefiner
from cortex.memory.shannon import ShannonCompactor
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.maxwell_daemon")


class MaxwellDaemon:
    """Information density enforcement daemon."""

    def __init__(self, engine: Any):
        self._engine = engine
        self._shannon_compactor = ShannonCompactor()
        if hasattr(engine, "shannon") and engine.shannon:
            self._shannon_compactor = engine.shannon

        # Ω₄: Sovereign Architectural Refinement
        self._refiner = SovereignRefiner(os.getcwd())

    async def intercept_bus_event(self, payload: str) -> Result[str, str]:
        """Measure Shannon density of the string before passing to next layer."""
        if not payload or not self._shannon_compactor:
            return Ok(payload)

        logger.debug("MaxwellDaemon analyzing event density...")

        # AX-042: KV-Aware Routing & Exergy Optimization
        # Calculate entropy of the string.
        tokens = list(payload)
        entropy = self._shannon_compactor.calculate_entropy(tokens)
        size = len(payload)

        # density = bits per character (0.0 to approx 8.0 for UTF-8)
        density = entropy

        # Reject if below threshold (Thermal Noise)
        # Threshold 0.05 bits/char = effectively zero information.
        if size > 100 and density < 0.05:
            logger.warning("MaxwellDaemon REJECTED thermal noise (density: %.4f)", density)
            return Err("THERMAL_NOISE_REJECTED")

        return Ok(payload)

    def trigger_architectural_refinement(self):
        """
        Manages the exergy calculation of the code and proposes distillations (Ω₄).
        """
        logger.info("Executing Maxwell's Exergy Refinement Pass...")
        ghosts_found = self._refiner.distill_architecture()
        if ghosts_found > 0:
            logger.warning("[MAXWELL] %d code ghosts detected.", ghosts_found)
        else:
            logger.info("[MAXWELL] Exergy check passed. High structural density.")
        return ghosts_found
