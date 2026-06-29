# [C5-REAL] Exergy-Maximized
"""CORTEX Meta-Arbiter — Dual-Substrate Arbitration Engine (Facade).

Provides two primary executive layers:
1. MetaArbiter (Cognitive Arbitration): Resolves inter-layer contradictions
   using weighted evidence fusion across the cognitive substrates.
2. MetaArbiterKernel (Thermodynamic Trace Collapse): collapse operator for
   ExecutionTrace objects, as specified in the E1 profiler blueprint.

Note: This file is a facade. Implementation has been extracted to:
- meta_arbiter_types.py
- cognitive_arbiter.py
- meta_arbiter_kernel.py

Reality Level: C5-REAL
"""

from __future__ import annotations

from babylon60.engine.meta.cognitive_arbiter import MetaArbiter
from babylon60.engine.meta.meta_arbiter_kernel import (
    CollapseReceipt,
    MetaArbiterKernel,
    TrajectoryScore,
)
from babylon60.engine.meta.meta_arbiter_types import (
    ArbiterVerdict,
    ConflictPair,
    LayerID,
    LayerSignal,
    Resolution,
)

# Re-export definitions for compatibility
__all__ = [
    "ArbiterVerdict",
    "CollapseReceipt",
    "ConflictPair",
    "LayerID",
    "LayerSignal",
    "MetaArbiter",
    "MetaArbiterKernel",
    "Resolution",
    "TrajectoryScore",
]
