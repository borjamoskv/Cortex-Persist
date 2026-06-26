# [C5-REAL] Exergy-Maximized
"""Causality Module.

Taint propagation, causal DAG integrity, and effective confidence
recomputation. Implements Axiom Ω₁₃ thermodynamic enforcement:
without taint propagation, downstream modules optimize over cadáveres perfumados.

Status: IMPLEMENTED (upgraded from PARTIAL via Ω₁₃ enforcement).
"""

from __future__ import annotations

from cortex_extensions.causality.models import Confidence, FactNode, TaintStatus
from cortex_extensions.causality.taint import (
    downgrade_confidence,
    propagate_taint,
    recompute_effective_confidence,
)

__all__ = [
    "Confidence",
    "FactNode",
    "TaintStatus",
    "downgrade_confidence",
    "propagate_taint",
    "recompute_effective_confidence",
]
