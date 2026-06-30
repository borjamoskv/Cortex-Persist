# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Thermodynamic Memory Engrams.

Translates biological connectomics and somatic homeostasis into actionable code.
Engrams are functionally stable embeddings wrapped in metabolic energy levels.
"""

from __future__ import annotations

import time

from pydantic import Field

from babylon60.memory.models import CortexFactModel


class CortexSemanticEngram(CortexFactModel):
    """Computable Engram representing active, metabolically decaying memory.

    Inherits from CortexFactModel to retain compatibility with L2 Vector Store,
    but adds Thermodynamic Engine attributes (LTP, Decay, Connectivity).
    """

    energy_level: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Current synaptic strength (LTP). Modulated only by empirical retrieval and failures.",
    )
    entangled_refs: list[str] = Field(
        default_factory=list,
        description="UUIDs of semantically linked engrams (connectomics).",
    )
    last_accessed: float = Field(
        default_factory=time.time, description="Unix timestamp of last structural retrieval."
    )

    def access(self, boost: float = 0.2) -> None:
        """Process a retrieval event, boosting synaptic energy (simulate LTP)."""
        object.__setattr__(self, "last_accessed", time.time())
        object.__setattr__(self, "energy_level", min(1.0, self.energy_level + boost))

    def decay(self, penalty: float = 0.05) -> None:
        """Process an LTD event (Long-Term Depression), reducing synaptic energy."""
        object.__setattr__(self, "energy_level", max(0.0, self.energy_level - penalty))

    def compute_decay(self, decay_rate_per_day: float = 0.05) -> float:
        """Deprecated: Returns current energy_level to satisfy legacy calls without dynamic temporal decay."""
        return self.energy_level
