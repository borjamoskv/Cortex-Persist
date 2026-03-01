# cortex/sovereign/bio_idc.py
"""Biologically Modulated Active Inference Bridge.

Maps DigitalEndocrine hormone levels to Active Inference EFE parameters,
enabling the agent's decision-making to respond to stress, curiosity,
fatigue, and trust states in real-time.

Phase 4: Supports pharmacological modulation via substance injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from cortex.sovereign.endocrine import DigitalEndocrine, Substance
    from idc_core import ActiveInferenceEngine


class BiologicallyModulatedEngine:
    """Bridges Endocrine state to IDC decision making.

    Hormone → EFE weight mapping:
    - Cortisol  → ↑ risk_weight  (risk aversion under stress)
    - Dopamine  → ↓ ambiguity_weight  (curiosity-driven exploration)
    - Melatonin → ↑ risk_weight + ↓ ambiguity_weight  (conservative sleep mode)
    - Oxytocin  → ↓ risk_weight  (trust lowers perceived threat)
    """

    def __init__(
        self, engine: ActiveInferenceEngine, endocrine: DigitalEndocrine,
    ) -> None:
        self.engine = engine
        self.endocrine = endocrine

    def get_efe_weights(self) -> tuple[float, float]:
        """Calculate EFE weights from current hormonal state.

        Returns:
            (risk_weight, ambiguity_weight) tuple.
        """
        # Cortisol: panic amplifies risk aversion → [1.0, 6.0]
        risk_weight = 1.0 + (self.endocrine.cortisol * 5.0)

        # Dopamine: curiosity suppresses ambiguity penalty → [0.05, 1.0]
        ambiguity_weight = 1.0 - (self.endocrine.dopamine * 0.95)

        # Melatonin: fatigue → conservative (higher risk, lower curiosity)
        risk_weight += self.endocrine.melatonin * 2.0
        ambiguity_weight += self.endocrine.melatonin * 0.5

        # Oxytocin: trust → lower risk aversion (collaborative openness)
        risk_weight = max(0.1, risk_weight - self.endocrine.oxytocin * 1.5)

        return float(risk_weight), float(ambiguity_weight)

    def choose_action(
        self,
        belief: np.ndarray,
        likelihood_matrix: np.ndarray,
        preferences: np.ndarray,
        transition_matrices: np.ndarray,
    ) -> int:
        """Choose action using biologically modulated EFE."""
        rw, aw = self.get_efe_weights()
        return self.engine.choose_action(
            belief, likelihood_matrix, preferences, transition_matrices,
            risk_weight=rw, ambiguity_weight=aw,
        )

    # ── Phase 4: Pharmacological pass-through ───────────────────────

    def inject(self, substance: Substance) -> None:
        """Inject a substance into the underlying endocrine system."""
        self.endocrine.inject(substance)

    def inject_many(self, substances: list[Substance]) -> None:
        """Inject multiple substances (compound agents)."""
        self.endocrine.inject_many(substances)

    def clear(self, target: str | None = None) -> int:
        """Clear active substances from the endocrine system."""
        return self.endocrine.clear(target)

    @property
    def pharmacological_state(self) -> dict:
        """Current pharmacological state for diagnostics."""
        return {
            "efe_weights": dict(zip(
                ("risk_weight", "ambiguity_weight"), self.get_efe_weights(), strict=True,
            )),
            "active_substances": [
                {
                    "name": s.name,
                    "target": s.target,
                    "mode": s.mode,
                    "effective_potency": round(s.effective_potency, 3),
                    "remaining_life": round(s.remaining_life, 1),
                }
                for s in self.endocrine.active_substances
            ],
        }
