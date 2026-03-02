"""
CORTEX V7 — Digital Endocrine System (Hormonal Homeostasis).

Regulates system-wide behavior using hormonal signals (Cortisol, Neural-Growth).
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Dict

logger = logging.getLogger("cortex.endocrine")


class HormoneType(Enum):
    CORTISOL = auto()  # Stress, Latency, Failure
    NEURAL_GROWTH = auto()  # Stability, Success, Bridge formation
    ADRENALINE = auto()  # Crisis, Critical Error, Immediate Reflex
    DOPAMINE = auto()  # Reward, Repetitive Success, Satiation


class EndocrineRegistry:
    """Singleton hormonal registry for CORTEX."""

    _instance: EndocrineRegistry | None = None

    def __new__(cls) -> EndocrineRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._hormones = {
                HormoneType.CORTISOL: 0.1,
                HormoneType.NEURAL_GROWTH: 0.5,
                HormoneType.ADRENALINE: 0.0,
                HormoneType.DOPAMINE: 0.2,
            }
            # Ω₂: Decay constants (per interaction/tick)
            cls._instance._decay = {
                HormoneType.CORTISOL: 0.005,
                HormoneType.NEURAL_GROWTH: 0.001,
                HormoneType.ADRENALINE: 0.2,  # Adrenaline dissipates VERY fast
                HormoneType.DOPAMINE: 0.01,
            }
        return cls._instance

    def get_level(self, hormone: HormoneType) -> float:
        return self._hormones.get(hormone, 0.0)

    def pulse(self, hormone: HormoneType, delta: float, reason: str | None = None) -> float:
        """Adjust local hormonal levels (clamped 0.0-1.0)."""
        # Ω₅: Natural decay trigger before pulse
        self._apply_decay()

        current = self._hormones.get(hormone, 0.0)
        new_val = max(0.0, min(1.0, current + delta))
        self._hormones[hormone] = new_val

        if abs(delta) > 0.05 or new_val > 0.8:
            logger.info(
                "🧬 [ENDOCRINE] %s pulse: %.2f -> %.2f (Δ %.2f) | Reason: %s",
                hormone.name,
                current,
                new_val,
                delta,
                reason or "Topological drift",
            )
        return new_val

    def sync_with_calcification(self, index: float) -> None:
        """
        Ω₅-H: Sync systemic Cortisol with project Calcification Index.
        Threshold: Index > 50 starts increasing Cortisol significantly.
        """
        # Baseline stress from calcification (0.0 to 1.0)
        # 0 index -> 0 stress. 100 index -> 1.0 stress (clamped).
        calc_stress = min(1.0, index / 100.0)

        # We don't overwrite, we 'pull' Cortisol towards this baseline if it's higher
        current = self.get_level(HormoneType.CORTISOL)
        if calc_stress > current:
            self.pulse(
                HormoneType.CORTISOL,
                (calc_stress - current) * 0.5,
                reason=f"Ω₂-C Drift (Index: {index:.2f})"
            )

    def _apply_decay(self) -> None:
        """Applies entropic decay to all hormones (Ω₂)."""
        for h, current in self._hormones.items():
            decay_rate = self._decay.get(h, 0.0)
            self._hormones[h] = max(0.0, current - decay_rate)

    @property
    def balance(self) -> Dict[str, float]:
        """Returns current hormonal state for telemetry."""
        return {h.name: round(v, 3) for h, v in self._hormones.items()}


ENDOCRINE = EndocrineRegistry()
