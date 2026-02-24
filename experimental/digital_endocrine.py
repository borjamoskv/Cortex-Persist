# digital_endocrine.py
"""Digital Endocrine system for adaptive LLM behavior.

The module defines a `DigitalEndocrine` class that tracks virtual hormone levels
(cortisol, dopamine, serotonin, adrenaline) based on detected context cues.
It exposes a `temperature` property that can be queried by the LLM inference
layer to adjust creativity, as well as a `response_style` helper that maps the
current hormonal state to a high‑level response mode.

This implementation is deliberately lightweight and pure‑Python so it can be
imported in any CORTEX environment without external dependencies.
"""

from __future__ import annotations
from typing import Set


class DigitalEndocrine:
    """Virtual endocrine system that modulates LLM hyper‑parameters.

    The system is inspired by the *synthetic psychology* concept described in the
    design document. Hormone levels are floats in the range ``[0.0, 1.0]`` where
    ``0.0`` means the hormone is absent and ``1.0`` means maximal secretion.
    """

    def __init__(self) -> None:
        self.cortisol: float = 0.0   # stress – forces low temperature, terse output
        self.dopamine: float = 0.5   # creativity – raises temperature, divergent ideas
        self.serotonin: float = 0.5  # confidence – stabilises response style
        self.adrenaline: float = 0.0 # alert – triggers cautious verification

    # ---------------------------------------------------------------------
    # Context detection – simple keyword based heuristics (replace with a more
    # sophisticated classifier when needed).
    # ---------------------------------------------------------------------
    def ingest_context(self, message: str, metadata: dict | None = None) -> None:
        """Update hormone levels based on the incoming user message.

        Parameters
        ----------
        message: str
            Raw user input.
        metadata: dict | None
            Optional extra data (e.g. UI event timestamps, error codes).
        """
        if metadata is None:
            metadata = {}
        words: Set[str] = set(message.lower().split())

        # urgency / error keywords → cortisol spike
        urgency = {"urgente", "error", "fallo", "crash", "asap", "critical"}
        # creative / brainstorming keywords → dopamine boost
        creative = {"ideas", "brainstorm", "explora", "imagin", "qué tal si"}
        # positive feedback → serotonin increase
        positive = {"gracias", "bien", "excelente", "perfecto", "genial"}
        # high‑risk / unknown → adrenaline rise
        risk = {"captcha", "render", "3d", "desconocido", "inseguro"}

        if words & urgency:
            self.cortisol = min(1.0, self.cortisol + 0.4)
            self.dopamine = max(0.0, self.dopamine - 0.2)
        if words & creative:
            self.dopamine = min(1.0, self.dopamine + 0.4)
            self.cortisol = max(0.0, self.cortisol - 0.2)
        if words & positive:
            self.serotonin = min(1.0, self.serotonin + 0.3)
        if words & risk:
            self.adrenaline = min(1.0, self.adrenaline + 0.3)

        # decay a small amount each call to avoid saturation
        self._decay()

    # ---------------------------------------------------------------------
    def _decay(self) -> None:
        """Gradual decay of hormone levels to model homeostasis."""
        decay_factor = 0.05
        self.cortisol = max(0.0, self.cortisol - decay_factor)
        self.dopamine = max(0.0, self.dopamine - decay_factor)
        self.serotonin = max(0.0, self.serotonin - decay_factor)
        self.adrenaline = max(0.0, self.adrenaline - decay_factor)

    # ---------------------------------------------------------------------
    @property
    def temperature(self) -> float:
        """Dynamic temperature derived from hormone levels.

        Base temperature is 0.5. Dopamine pushes it up, cortisol pulls it down.
        The formula is deliberately simple but captures the intended behaviour.
        """
        base = 0.5
        temp = base + 0.4 * self.dopamine - 0.5 * self.cortisol
        # clamp to the valid range for LLM temperature
        return max(0.0, min(1.0, temp))

    @property
    def response_style(self) -> str:
        """High‑level style hint for downstream rendering.

        Returns one of ``"telegraphic"``, ``"expansive"``, ``"cautious"`` or
        ``"balanced"`` based on the dominant hormone.
        """
        if self.cortisol > 0.7:
            return "telegraphic"
        if self.dopamine > 0.7:
            return "expansive"
        if self.adrenaline > 0.5:
            return "cautious"
        return "balanced"

    # ---------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a serialisable snapshot of the current hormonal state."""
        return {
            "cortisol": self.cortisol,
            "dopamine": self.dopamine,
            "serotonin": self.serotonin,
            "adrenaline": self.adrenaline,
            "temperature": self.temperature,
            "response_style": self.response_style,
        }

# Example usage (remove in production code)
if __name__ == "__main__":
    de = DigitalEndocrine()
    de.ingest_context("Necesito una solución urgente para este error crítico")
    print(de.snapshot())
```
