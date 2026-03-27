"""
CORTEX V7 — Thermodynamic Gradient Management (Equilibrium).

Regulates system-wide behavior using gradient signals (Pressure, Expansion-Coefficient).
"""

from __future__ import annotations

import logging
import time
from enum import Enum, auto

logger = logging.getLogger("cortex.gradient")


class GradientType(Enum):
    PRESSURE = auto()  # Stress, Latency, Failure (Cortisol)
    EXPANSION_COEFFICIENT = auto()  # Stability, Success, Bridge formation (Neural-Growth)
    KINETIC_BURST = auto()  # Crisis, Critical Error, Immediate Reflex (Adrenaline)
    CATALYTIC_REWARD = auto()  # Reward, Repetitive Success, Satiation (Dopamine)
    HOMEOSTATIC_EQUILIBRIUM = auto()  # Long-term stability, homeostasis (Serotonin)


class GradientRegistry:
    """Singleton gradient registry for CORTEX with Ω-Standard Homeostasis."""

    _instance: GradientRegistry | None = None

    def __new__(cls) -> GradientRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._gradients = {  # type: ignore[reportAttributeAccessIssue]
                GradientType.PRESSURE: 0.1,
                GradientType.EXPANSION_COEFFICIENT: 0.5,
                GradientType.KINETIC_BURST: 0.0,
                GradientType.CATALYTIC_REWARD: 0.2,
                GradientType.HOMEOSTATIC_EQUILIBRIUM: 0.5,
            }
            # Ω₂: Decay constants (per interaction/tick)
            cls._instance._decay = {  # type: ignore[reportAttributeAccessIssue]
                GradientType.PRESSURE: 0.005,
                GradientType.EXPANSION_COEFFICIENT: 0.001,
                GradientType.KINETIC_BURST: 0.2,
                GradientType.CATALYTIC_REWARD: 0.01,
                GradientType.HOMEOSTATIC_EQUILIBRIUM: 0.0005,
            }
            cls._instance._last_pulse = dict.fromkeys(GradientType, 0.0)  # type: ignore[reportAttributeAccessIssue]
        return cls._instance

    def get_level(self, gradient: GradientType) -> float:
        self._apply_decay()
        return self._gradients.get(gradient, 0.0)  # type: ignore[reportAttributeAccessIssue]

    def pulse(self, gradient: GradientType, delta: float, reason: str | None = None) -> float:
        """Adjust local gradient levels (clamped 0.0-1.0)."""
        current = self._gradients.get(gradient, 0.0)  # type: ignore[reportAttributeAccessIssue]
        new_val = max(0.0, min(1.0, current + delta))
        self._gradients[gradient] = new_val  # type: ignore[reportAttributeAccessIssue]
        self._last_pulse[gradient] = time.time()  # type: ignore[reportAttributeAccessIssue]

        if abs(delta) > 0.05 or new_val > 0.8:
            logger.info(
                "🧬 [GRADIENT] %s pulse: %.2f -> %.2f (Δ %.2f) | Reason: %s",
                gradient.name,
                current,
                new_val,
                delta,
                reason or "Topological drift",
            )

        # Ω₄: Aesthetic / Harmonic balance: High Reward triggers Equilibrium
        if gradient == GradientType.CATALYTIC_REWARD and new_val > 0.7:
            self.pulse(
                GradientType.HOMEOSTATIC_EQUILIBRIUM,
                0.05,
                "Catalytic-Reward-to-Equilibrium synthesis",
            )

        return new_val

    def sync_with_calcification(self, index: float) -> None:
        """Ω₅-H: Sync systemic Pressure with project Calcification Index."""
        calc_stress = min(1.0, index / 100.0)
        current = self._gradients.get(GradientType.PRESSURE, 0.0)  # type: ignore[reportAttributeAccessIssue]
        if calc_stress > current:
            self.pulse(
                GradientType.PRESSURE,
                (calc_stress - current) * 0.5,
                reason=f"Calcification Stress (Index: {index:.2f})",
            )

    def prune(self) -> int:
        """
        Ω₆-P: Dynamic Pruning.
        Removes stagnant gradient effects and forces baseline return.
        Returns count of gradients pruned.
        """
        count = 0
        for h, val in self._gradients.items():  # type: ignore[reportAttributeAccessIssue]
            # If a gradient is very low and hasn't changed, 'zero' it
            if val < 0.01:
                self._gradients[h] = 0.0  # type: ignore[reportAttributeAccessIssue]
                count += 1
        return count

    def _apply_decay(self) -> None:
        """Applies entropic decay to all gradients (Ω₂)."""
        for h, current in self._gradients.items():  # type: ignore[reportAttributeAccessIssue]
            decay_rate = self._decay.get(h, 0.0)  # type: ignore[reportAttributeAccessIssue]
            self._gradients[h] = max(0.0, current - decay_rate)  # type: ignore[reportAttributeAccessIssue]

    @property
    def balance(self) -> dict[str, float]:
        """Returns current gradient state for telemetry."""
        return {h.name: round(v, 3) for h, v in self._gradients.items()}  # type: ignore[reportAttributeAccessIssue]


GRADIENT = GradientRegistry()
