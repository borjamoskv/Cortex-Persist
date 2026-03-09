"""
CORTEX V5 - IMMUNE-SYSTEM-V1 (The Epistemic Arbitrator).
Interprets and arbitrates signals between perception and execution.
"""

from cortex.immune.arbiter import FilterResult, ImmuneArbiter, TriageResult, Verdict
from cortex.immune.error_boundary import ErrorBoundary, error_boundary
from cortex.immune.falsification import EvolutionaryFalsifier

__all__ = [
    "ErrorBoundary",
    "EvolutionaryFalsifier",
    "FilterResult",
    "ImmuneArbiter",
    "TriageResult",
    "Verdict",
    "error_boundary",
]

