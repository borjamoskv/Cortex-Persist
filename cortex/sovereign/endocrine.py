# cortex/sovereign/endocrine.py
"""Digital Endocrine system for adaptive Sovereign behavior.

Modulates agent hyperparameters (temperature, response mode) based on virtual 
hormone levels (cortisol, dopamine, serotonin, adrenaline) derived from 
contextual cues and system health metrics.
"""

from __future__ import annotations
import logging
from typing import Set

logger = logging.getLogger(__name__)

class DigitalEndocrine:
    """Virtual endocrine system for Sovereign Agentic Modality."""

    def __init__(self) -> None:
        self.cortisol: float = 0.0   # Stress/Urgency
        self.dopamine: float = 0.5   # Creativity/Exploration
        self.serotonin: float = 0.5  # Confidence/Success
        self.adrenaline: float = 0.0 # Alert/Risk
        self.oxytocin: float = 0.5   # Trust/Collaboration

    def ingest_context(self, message: str, metadata: dict | None = None) -> None:
        """Update hormone levels based on incoming context telemetry with damping."""
        if metadata is None:
            metadata = {}
        words: Set[str] = set(message.lower().split())

        # Damping factor (Exponential Moving Average)
        # alpha = 1.0 means instant change
        # alpha = 0.3 means 30% contribution from new signal
        alpha = 0.3

        # Stress Response
        if any(w in words for w in ["urgente", "error", "fallo", "crash", "critical", "panic"]):
            self.cortisol = min(1.0, self.cortisol + (0.45 * alpha))
            self.dopamine = max(0.0, self.dopamine - (0.25 * alpha))

        # Creative Stimulus
        if any(w in words for w in ["ideas", "brainstorm", "explora", "innovar", "imagina"]):
            self.dopamine = min(1.0, self.dopamine + (0.4 * alpha))
            self.cortisol = max(0.0, self.cortisol - (0.2 * alpha))

        # Dopamine/Serotonin Reward
        if any(w in words for w in ["gracias", "bien", "mejorado", "perfecto", "genial"]):
            self.serotonin = min(1.0, self.serotonin + (0.3 * alpha))
            self.dopamine = min(1.0, self.dopamine + (0.1 * alpha))

        # Trust/Collaboration (Oxytocin)
        if any(w in words for w in ["colaborar", "equipo", "juntos", "unificado", "nexus"]):
            self.oxytocin = min(1.0, self.oxytocin + (0.4 * alpha))
            self.serotonin = min(1.0, self.serotonin + (0.15 * alpha))

        # Threat Detection
        if any(w in words for w in ["inseguro", "desconocido", "riesgo", "bypass", "vulnerabilidad"]):
            self.adrenaline = min(1.0, self.adrenaline + (0.5 * alpha))

        self._homeostasis()

    def _homeostasis(self) -> None:
        """Gradual hormone decay to maintain system balance."""
        decay = 0.02
        self.cortisol = max(0.0, self.cortisol - decay)
        self.dopamine = max(0.0, self.dopamine - (decay * 0.5))
        self.serotonin = max(0.0, self.serotonin - (decay * 0.5))
        self.adrenaline = max(0.0, self.adrenaline - (decay * 2))
        self.oxytocin = max(0.0, self.oxytocin - (decay * 0.1))

    @property
    def temperature(self) -> float:
        """Dynamic temperature derived from hormonal state."""
        base = 0.5
        # Refined formula: stress lowers temp (narrower/stiffer), dopamine raises (wilder/fresher)
        temp = base + 0.5 * self.dopamine - 0.6 * self.cortisol
        # GPT-4o Wave Fix: Hard floor at 0.1 rather than 0.0 to prevent zero-temp generative lockup.
        return max(0.1, min(1.0, temp))

    @property
    def response_style(self) -> str:
        """High-level stylistic hint for Sovereign output."""
        if self.cortisol > 0.8:
            return "telegraphic"
        if self.adrenaline > 0.6:
            return "cautious"
        if self.dopamine > 0.8:
            return "expansive"
        return "balanced"

    def to_dict(self) -> dict:
        """Return the current biological state of the agent."""
        return {
            "hormones": {
                "cortisol": round(self.cortisol, 3),
                "dopamine": round(self.dopamine, 3),
                "serotonin": round(self.serotonin, 3),
                "adrenaline": round(self.adrenaline, 3),
                "oxytocin": round(self.oxytocin, 3),
            },
            "temperature": round(self.temperature, 2),
            "style": self.response_style,
        }

