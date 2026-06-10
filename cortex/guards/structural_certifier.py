# [C5-REAL] Exergy-Maximized
"""CORTEX - Structural Certifier.

A formal validation guard that verifies if a given string payload qualifies as
"Structural Condensation" (e.g., valid JSON, array of dicts). Used to enforce
causal closure rules where mere prose is rejected.
"""

import json
from enum import Enum, auto


class StructuralGrade(Enum):
    """Grading levels for structural validation."""

    ACCEPTED = auto()
    """Fully compliant with expected structural rules (e.g. JSON array of dicts)."""

    WEAKLY_STRUCTURAL = auto()
    """Valid formal structure (e.g. valid JSON) but missing the specific shape constraint."""

    INVALID_CANDIDATE = auto()
    """Fails structural parsing entirely (e.g. malformed JSON or pure narrative prose)."""


class StructuralCertifier:
    """Certifies whether payload contents meet structural rigor."""

    @staticmethod
    def certify_structure(payload: str) -> StructuralGrade:
        """Evaluates a text payload for formal JSON/array-of-dicts structure.

        Args:
            payload: The text string to validate.

        Returns:
            StructuralGrade indicating the level of validation passed.
        """
        payload = payload.strip()
        if not payload:
            return StructuralGrade.INVALID_CANDIDATE

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return StructuralGrade.INVALID_CANDIDATE

        # To match the behavior previously enforced via regex:
        # Require it to be a non-empty list containing only dicts.
        if isinstance(parsed, list) and len(parsed) > 0 and all(isinstance(item, dict) for item in parsed):
            return StructuralGrade.ACCEPTED

        return StructuralGrade.WEAKLY_STRUCTURAL
