"""CORTEX v6+ — Thermodynamic Memory Engrams.

Translates biological connectomics and somatic homeostasis into actionable code.
Engrams are functionally stable embeddings wrapped in metabolic energy levels.
"""

from __future__ import annotations

import time

from pydantic import Field

from cortex.memory.models import CortexFactModel


class CortexSemanticEngram(CortexFactModel):
    """Computable Engram representing active, metabolically decaying memory.

    Inherits from CortexFactModel to retain compatibility with L2 Vector Store,
    but adds Thermodynamic Engine attributes (LTP, Decay, Connectivity).
    """

    energy_level: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Current synaptic strength (LTP). Decays over time if not accessed.",
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

    def compute_decay(self, decay_rate_per_day: float = 0.05) -> float:
        """Calculate the current actual energy accounting for temporal decay."""
        days_since_access = max(0.0, (time.time() - self.last_accessed) / 86400.0)
        decayed = self.energy_level - (days_since_access * decay_rate_per_day)
        return max(0.0, float(decayed))
