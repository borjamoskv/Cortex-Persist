# [C5-REAL] Exergy-Maximized
"""Pipeline orchestrator exceptions.

Reality Level: C5-REAL
"""

from __future__ import annotations


class BudgetExhaustedError(RuntimeError):
    """Raised when a mission exceeds its Ω₃ exergy ceiling."""


class PipelineCancelledError(RuntimeError):
    """Raised when a pipeline run is cancelled externally."""
