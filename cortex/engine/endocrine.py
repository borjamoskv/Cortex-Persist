"""
CORTEX V7 — Digital Endocrine System (Hormonal Homeostasis).

Regulates system-wide behavior using hormonal signals (Cortisol, Neural-Growth).
"""

from __future__ import annotations

import logging
import time
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger("cortex.endocrine")


class HormoneType(Enum):
    CORTISOL = auto()  # Stress, Latency, Failure
    NEURAL_GROWTH = auto()  # Stability, Success, Bridge formation
    ADRENALINE = auto()  # Crisis, Critical Error, Immediate Reflex
    DOPAMINE = auto()  # Reward, Repetitive Success, Satiation
    SEROTONIN = auto()  # Long-term stability, homeostasis


class EndocrineRegistry:
    """Singleton hormonal registry for CORTEX with Ω-Standard Homeostasis."""

    _instance: Optional[EndocrineRegistry] = None

    def __new__(cls) -> EndocrineRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._hormones = {  # type: ignore[reportAttributeAccessIssue]
                HormoneType.CORTISOL: 0.1,
                HormoneType.NEURAL_GROWTH: 0.5,
                HormoneType.ADRENALINE: 0.0,
                HormoneType.DOPAMINE: 0.2,
                HormoneType.SEROTONIN: 0.5,
            }
            # Ω₂: Decay constants (per interaction/tick)
            cls._instance._decay = {  # type: ignore[reportAttributeAccessIssue]
                HormoneType.CORTISOL: 0.005,
                HormoneType.NEURAL_GROWTH: 0.001,
                HormoneType.ADRENALINE: 0.2,
                HormoneType.DOPAMINE: 0.01,
                HormoneType.SEROTONIN: 0.0005,
            }
            cls._instance._last_pulse = dict.fromkeys(HormoneType, 0.0)  # type: ignore[reportAttributeAccessIssue]
        return cls._instance

    def get_level(self, hormone: HormoneType) -> float:
        self._apply_decay()
        return self._hormones.get(hormone, 0.0)  # type: ignore[reportAttributeAccessIssue]

    def pulse(self, hormone: HormoneType, delta: float, reason: Optional[str] = None) -> float:
        """Adjust local hormonal levels (clamped 0.0-1.0)."""
        current = self._hormones.get(hormone, 0.0)  # type: ignore[reportAttributeAccessIssue]
        new_val = max(0.0, min(1.0, current + delta))
        self._hormones[hormone] = new_val  # type: ignore[reportAttributeAccessIssue]
        self._last_pulse[hormone] = time.time()  # type: ignore[reportAttributeAccessIssue]

        if abs(delta) > 0.05 or new_val > 0.8:
            logger.info(
                "🧬 [ENDOCRINE] %s pulse: %.2f -> %.2f (Δ %.2f) | Reason: %s",
                hormone.name,
                current,
                new_val,
                delta,
                reason or "Topological drift",
            )

        # Ω₄: Aesthetic / Harmonic balance: High Dopamine triggers Serotonin
        if hormone == HormoneType.DOPAMINE and new_val > 0.7:
            self.pulse(HormoneType.SEROTONIN, 0.05, "Dopamine-to-Serotonin synthesis")

        return new_val

    def sync_with_calcification(self, index: float) -> None:
        """Ω₅-H: Sync systemic Cortisol with project Calcification Index."""
        calc_stress = min(1.0, index / 100.0)
        current = self._hormones.get(HormoneType.CORTISOL, 0.0)  # type: ignore[reportAttributeAccessIssue]
        if calc_stress > current:
            self.pulse(
                HormoneType.CORTISOL,
                (calc_stress - current) * 0.5,
                reason=f"Calcification Stress (Index: {index:.2f})",
            )

    def prune(self) -> int:
        """
        Ω₆-P: Dynamic Pruning.
        Removes stagnant hormonal effects and forces baseline return.
        Returns count of hormones pruned.
        """
        count = 0
        for h, val in self._hormones.items():  # type: ignore[reportAttributeAccessIssue]
            # If a hormone is very low and hasn't changed, 'zero' it
            if val < 0.01:
                self._hormones[h] = 0.0  # type: ignore[reportAttributeAccessIssue]
                count += 1
        return count

    def _apply_decay(self) -> None:
        """Applies entropic decay to all hormones (Ω₂)."""
        for h, current in self._hormones.items():  # type: ignore[reportAttributeAccessIssue]
            decay_rate = self._decay.get(h, 0.0)  # type: ignore[reportAttributeAccessIssue]
            self._hormones[h] = max(0.0, current - decay_rate)  # type: ignore[reportAttributeAccessIssue]

    @property
    def balance(self) -> dict[str, float]:
        """Returns current hormonal state for telemetry."""
        return {h.name: round(v, 3) for h, v in self._hormones.items()}  # type: ignore[reportAttributeAccessIssue]


ENDOCRINE = EndocrineRegistry()
