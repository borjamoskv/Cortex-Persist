from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.immune.breaker")


@dataclass
class EpistemicState:
    """Represents the current cognitive entropy (thrashing) level of the system."""

    consecutive_test_failures: int = 0
    unresolved_ghosts: int = 0
    recent_linting_mutations: int = 0
    time_window_minutes: int = 15

    @property
    def entropy_density(self) -> float:
        """
        Calcula la Densidad Entrópica (ED).
        Si un LLM está adivinando, pytest y linter se quejarán repetidamente.
        """
        base_noise = self.consecutive_test_failures * 15
        ghost_noise = self.unresolved_ghosts * 10
        thrashing = self.recent_linting_mutations * 5

        # Métrica adimensional 0-100+
        return float(base_noise + ghost_noise + thrashing)


def evaluate_circuit_breaker(state: EpistemicState) -> dict[str, Any]:
    """
    Evalúa si debemos trips the breaker.
    Threshold: ED > 50 en la ventana de contexto.
    """
    TRIP_THRESHOLD = 50.0
    ed = state.entropy_density

    if ed > TRIP_THRESHOLD:
        return {
            "action": "TRIP_BREAKER",
            "reason": f"Entropy Density ({ed}) > Threshold ({TRIP_THRESHOLD}). System is hallucinating or thrashing.",
            "ed_score": ed,
        }
    return {"action": "ALLOW_CONTINUE", "ed_score": ed}


async def execute_circuit_trip(gap_description: str, cortex_engine: CortexEngine) -> dict[str, Any]:
    """Ejecuta la parada de emergencia y coordina la investigación."""

    # 1. Lock the system
    cortex_engine.set_system_state("LOCKED_EPISTEMIC_HALT")

    # 2. Persist the event using a non-standard bypass or directly via raw SQL if needed,
    # but since it's the engine itself locking it, we can force store if we pass an override,
    # or just log it if we can't store while locked.
    # Let's temporarily lift lock or use internal bypass if we implement it.
    # We will assume store() allows daemon writes if explicit source is given, or we just log.
    try:
        # We might need a flag in store() like `force=True` when locked.
        # But we'll try standard store first.
        await cortex_engine.store(
            type="error",
            project="system-kernel",
            source="daemon:circuit-breaker",
            confidence="C5",  # Absolute certainty of halt
            summary="SYSTEM HALTED: Entropy spike detected. Entering autodidact mode.",
            meta={"gap_identified": gap_description},
        )
    except Exception as e:
        logger.error("Failed to persist halt event: %s", e)

    # 3. Trigger Autodidact (mocked or actual if integrated)
    try:
        from cortex.agents.autodidact import force_ingestion

        axiom_id = await force_ingestion(query=gap_description)
    except ImportError:
        logger.warning("Autodidact-Omega not found. Halting indefinitely until manual resume.")
        axiom_id = None

    # 4. Release when axiom created
    if axiom_id:
        cortex_engine.set_system_state("ACTIVE")
        return {"status": "RESTORED", "new_axiom": axiom_id}

    return {"status": "HALTED", "reason": "Axiom not created or Autodidact missing."}
