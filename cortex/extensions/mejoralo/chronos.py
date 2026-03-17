"""CHRONOS-1 Yield Calculus (Axiom Ω₁₁).

Extracted from heal.py to maintain thermodynamic LOC limits.
"""

from cortex.extensions.mejoralo.constants import (
    CHRONOS_COMPLEXITY_DIVISOR,
    CHRONOS_HOURS_PER_CODEPATH,
    CHRONOS_HOURS_PER_FILE,
)


def calculate_chronos_yield(
    files_touched: int,
    codepaths_affected: int,
    runtime_ms: int,
    cyclomatic_complexity_delta: int,
) -> float:
    """Calculate linear hours saved per the CHRONOS-1 formula (Axiom Ω₁₁).

    Hours_Saved = ((files_touched * 6) + (codepaths_affected * 12)
                  + (runtime_ms * 10)) * (complexity_delta / 3) / 60
    """
    complexity_factor = abs(cyclomatic_complexity_delta) / max(1, CHRONOS_COMPLEXITY_DIVISOR)
    raw = (
        (files_touched * CHRONOS_HOURS_PER_FILE)
        + (codepaths_affected * CHRONOS_HOURS_PER_CODEPATH)
        + (runtime_ms * 10)
    ) * complexity_factor
    return round(raw / 60, 2)
