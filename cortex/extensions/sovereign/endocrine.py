# cortex/sovereign/endocrine.py
"""Digital Endocrine system for adaptive Sovereign behavior.

Modulates agent hyperparameters (temperature, response mode) based on virtual
hormone levels (cortisol, dopamine, serotonin, adrenaline) derived from
contextual cues and system health metrics.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DigitalEndocrine:
    """Virtual endocrine system for Sovereign Agentic Modality.

    Now multi-tenant isolated to prevent cross-tenant hormonal 'leakage'.
    """

    def __init__(self) -> None:
        self._tenant_states: dict[str, dict[str, float]] = {}

    def _get_state(self, tenant_id: str) -> dict[str, float]:
        if tenant_id not in self._tenant_states:
            self._tenant_states[tenant_id] = {
                "cortisol": 0.0,
                "dopamine": 0.5,
                "serotonin": 0.5,
                "adrenaline": 0.0,
                "oxytocin": 0.5,
            }
        return self._tenant_states[tenant_id]

    def ingest_context(
        self, message: str, tenant_id: str = "default", metadata: Optional[dict] = None
    ) -> None:
        """Update hormone levels based on incoming context telemetry with damping."""
        state = self._get_state(tenant_id)
        if metadata is None:
            metadata = {}
        words: set[str] = set(message.lower().split())

        # Damping factor (Exponential Moving Average)
        alpha = 0.3

        # Stress Response
        if words & {"urgente", "error", "fallo", "crash", "critical", "panic"}:
            state["cortisol"] = min(1.0, state["cortisol"] + (0.45 * alpha))
            state["dopamine"] = max(0.0, state["dopamine"] - (0.25 * alpha))

        # Creative Stimulus
        if words & {"ideas", "brainstorm", "explora", "innovar", "imagina"}:
            state["dopamine"] = min(1.0, state["dopamine"] + (0.4 * alpha))
            state["cortisol"] = max(0.0, state["cortisol"] - (0.2 * alpha))

        # Dopamine/Serotonin Reward
        if words & {"gracias", "bien", "mejorado", "perfecto", "genial"}:
            state["serotonin"] = min(1.0, state["serotonin"] + (0.3 * alpha))
            state["dopamine"] = min(1.0, state["dopamine"] + (0.1 * alpha))

        # Trust/Collaboration (Oxytocin)
        if words & {"colaborar", "equipo", "juntos", "unificado", "nexus"}:
            state["oxytocin"] = min(1.0, state["oxytocin"] + (0.4 * alpha))
            state["serotonin"] = min(1.0, state["serotonin"] + (0.15 * alpha))

        # Threat Detection
        if words & {"inseguro", "desconocido", "riesgo", "bypass", "vulnerabilidad"}:
            state["adrenaline"] = min(1.0, state["adrenaline"] + (0.5 * alpha))

        self._homeostasis(tenant_id)

    def _homeostasis(self, tenant_id: str) -> None:
        """Gradual hormone decay to maintain system balance."""
        state = self._get_state(tenant_id)
        decay = 0.02
        state["cortisol"] = max(0.0, state["cortisol"] - decay)
        state["dopamine"] = max(0.0, state["dopamine"] - (decay * 0.5))
        state["serotonin"] = max(0.0, state["serotonin"] - (decay * 0.5))
        state["adrenaline"] = max(0.0, state["adrenaline"] - (decay * 2))
        state["oxytocin"] = max(0.0, state["oxytocin"] - (decay * 0.1))

    def get_temperature(self, tenant_id: str = "default") -> float:
        """Dynamic temperature derived from hormonal state."""
        state = self._get_state(tenant_id)
        base = 0.5
        temp = base + 0.5 * state["dopamine"] - 0.6 * state["cortisol"]
        return max(0.1, min(1.0, temp))

    def get_response_style(self, tenant_id: str = "default") -> str:
        """High-level stylistic hint for Sovereign output."""
        state = self._get_state(tenant_id)
        if state["cortisol"] > 0.8:
            return "telegraphic"
        if state["adrenaline"] > 0.6:
            return "cautious"
        if state["dopamine"] > 0.8:
            return "expansive"
        return "balanced"

    def to_dict(self, tenant_id: str = "default") -> dict:
        """Return the current biological state of the agent."""
        state = self._get_state(tenant_id)
        return {
            "hormones": {k: float(f"{v:.3f}") for k, v in state.items()},
            "temperature": float(f"{self.get_temperature(tenant_id):.2f}"),
            "style": self.get_response_style(tenant_id),
        }

    @property
    def dopamine(self) -> float:
        """Helper to get default dopamine level."""
        return self._get_state("default")["dopamine"]

    @property
    def cortisol(self) -> float:
        """Helper to get default cortisol level."""
        return self._get_state("default")["cortisol"]
