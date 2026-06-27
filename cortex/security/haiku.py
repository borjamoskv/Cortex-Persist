# [C5-REAL] Exergy-Maximized
"""
[DEPRECATED] Haiku Guard (Ω₄): Aesthetic Integrity Validator for Sacred Truths.
This module has been deprecated in favor of `cortex.guards.landauer_guard.LandauerGuard`
due to the non-deterministic nature of phonetic heuristics.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Mapping
from typing import Any

from cortex.security.types import GuardViolation

logger = logging.getLogger("cortex.security.haiku")


class HaikuGuard:
    """[DEPRECATED] Validates the 5-7-5 structure (Ω₄)."""

    @staticmethod
    def validate(content: str) -> bool:
        """[DEPRECATED] Use LandauerGuard instead."""
        warnings.warn(
            "HaikuGuard is deprecated and will be removed. Use LandauerGuard instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return False

    @staticmethod
    def enforce(content: str, metadata: Mapping[str, Any]) -> None:
        """[DEPRECATED] Enforces Ω₄ for sacred artifacts."""
        warnings.warn(
            "HaikuGuard is deprecated and will be removed. Use LandauerGuard instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        is_sacred = metadata.get("fact_type") == "axiom" or "sacred" in metadata.get("tags", [])

        if is_sacred:
            raise GuardViolation(
                "Axiom rejected: HaikuGuard is deprecated. System requires LandauerGuard (Thermodynamic Compression)."
            )
