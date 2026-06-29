# [C5-REAL] Exergy-Maximized
"""
Landauer Guard (Ω₄): Thermodynamic Context Compression Validator.
Enforces Shannon Entropy and byte-size constraints on sacred truths to ensure absolute Exergy.
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from collections.abc import Mapping
from typing import Any

from babylon60.security.types import GuardViolation

logger = logging.getLogger("cortex.guards.landauer")


class LandauerGuard:
    """Validates the Thermodynamic Compression structure (Ω₄)."""

    MIN_ENTROPY = 3.5
    MAX_BYTES = 256

    @staticmethod
    def calculate_entropy(content: str) -> float:
        """Calculates Shannon Entropy of the string."""
        if not content:
            return 0.0
        counts = Counter(content)
        length = len(content)
        return -sum((count / length) * math.log2(count / length) for count in counts.values())

    @staticmethod
    def validate(content: str) -> bool:
        """
        Check if content follows the Landauer thermodynamic constraint.
        """
        content = content.strip()
        if not content:
            return False

        byte_len = len(content.encode("utf-8"))
        if byte_len > LandauerGuard.MAX_BYTES:
            logger.debug(
                "Landauer Guard: Axiom too large (Bytes: %d, Max: %d)",
                byte_len,
                LandauerGuard.MAX_BYTES,
            )
            return False

        entropy = LandauerGuard.calculate_entropy(content)
        if entropy < LandauerGuard.MIN_ENTROPY:
            logger.debug(
                "Landauer Guard: Axiom entropy too low (Entropy: %.2f, Min: %.2f)",
                entropy,
                LandauerGuard.MIN_ENTROPY,
            )
            return False

        return True

    @staticmethod
    def enforce(content: str, metadata: Mapping[str, Any]) -> None:
        """Enforces Ω₄ for sacred artifacts."""
        is_sacred = metadata.get("fact_type") == "axiom" or "sacred" in metadata.get("tags", [])

        if is_sacred and not LandauerGuard.validate(content):
            raise GuardViolation(
                f"Axiom rejected (Ω₄): Sacred truths must be thermodynamically compressed "
                f"(Shannon Entropy > {LandauerGuard.MIN_ENTROPY}, < {LandauerGuard.MAX_BYTES} bytes)."
            )
