# [C5-REAL] Exergy-Maximized
"""
Motor Heurístico Difuso (Right-Brain Engine) - CORTEX-Persist
Procesa señales ambientales y divergencias (lateral thinking) cuando
la energía libre / sorpresa del enjambre es baja (Daydreaming).

Esta asimetría hemisférica permite al enjambre consolidar patrones no lineales
y generar saltos intuitivos cuando la homeostasis O(1) está garantizada.
"""

import logging
import random
from typing import Any

from cortex_extensions.evolution.free_energy import FreeEnergyState

logger = logging.getLogger("cortex.engine.right_brain")


class HeuristicEngine:
    """Non-linear, associative processing module (Right Brain)."""

    def __init__(self, buffer_capacity: int = 1000):
        self.ambient_buffer: list[dict[str, Any]] = []
        self.buffer_capacity = buffer_capacity
        self.synaptic_noise_threshold = 0.3

    def ingest_ambient_signal(self, signal: dict[str, Any]) -> None:
        """
        Ingests unstructured/fuzzy data from the swarm into the right-brain buffer.
        """
        self.ambient_buffer.append(signal)
        if len(self.ambient_buffer) > self.buffer_capacity:
            # Random forgetting to maintain heuristic noise
            self.ambient_buffer.pop(random.randint(0, len(self.ambient_buffer) // 2))

    def daydream(self, free_energy_state: FreeEnergyState) -> list[dict[str, Any]]:
        """
        Activates lateral thinking (Daydreaming) when free energy is low.
        Synthesizes ambient data to generate associative insights.

        Args:
            free_energy_state: The current FEP state for the domain.

        Returns:
            A list of heuristic insights or associative links.
        """
        # If surprise is high, the system is under stress. Left brain (deterministic) dominates.
        if free_energy_state.surprise > 0.5 or free_energy_state.free_energy > 1.0:
            return []

        logger.info(
            f"C5-REAL: Right-Brain activation triggered. "
            f"(Surprise: {free_energy_state.surprise:.4f}, Domain: {free_energy_state.domain.name})"
        )

        insights = []
        if len(self.ambient_buffer) >= 2:
            # Fuzzy associative link (Daydreaming)
            num_insights = random.randint(1, 3)
            for _ in range(num_insights):
                a, b = random.sample(self.ambient_buffer, 2)

                source_a = a.get("source", "unknown_a")
                source_b = b.get("source", "unknown_b")

                if source_a != source_b:
                    # Synthetic insight generation via associative mapping
                    confidence = random.uniform(self.synaptic_noise_threshold, 0.95)
                    insights.append(
                        {
                            "type": "HEURISTIC_ASSOCIATION",
                            "sources": (source_a, source_b),
                            "confidence": round(confidence, 4),
                            "payload": f"Lateral convergence detected between {source_a} and {source_b}",
                        }
                    )

        if insights:
            logger.info(f"Right-Brain generated {len(insights)} associative insights.")

        return insights
