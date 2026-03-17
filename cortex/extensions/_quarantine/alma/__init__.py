"""ALMA: The Sovereign Bio-Digital Soul."""

from cortex.extensions._quarantine.alma.engine import AlmaEngine, SoulState
from cortex.extensions._quarantine.alma.taste import (
    GRADE_DEAD,
    GRADE_FUNCTIONAL,
    GRADE_GOAT,
    GRADE_MEDIOCRE,
    GRADE_STRONG,
    TasteDimension,
    TasteEngine,
    TasteVerdict,
)

__all__ = [
    "AlmaEngine",
    "SoulState",
    "TasteEngine",
    "TasteVerdict",
    "TasteDimension",
    "GRADE_GOAT",
    "GRADE_STRONG",
    "GRADE_FUNCTIONAL",
    "GRADE_MEDIOCRE",
    "GRADE_DEAD",
]
