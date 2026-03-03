"""
CORTEX V5 - IMMUNE-SYSTEM-V1 (The Epistemic Arbitrator).
Interprets and arbitrates signals between perception and execution.
"""

from cortex.immune.arbiter import FilterResult, ImmuneArbiter, TriageResult, Verdict
from cortex.immune.falsification import EvolutionaryFalsifier

__all__ = ["ImmuneArbiter", "EvolutionaryFalsifier", "Verdict", "TriageResult", "FilterResult"]
