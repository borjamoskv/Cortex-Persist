# cortex/evolution/psi_sap.py
"""
ψSAP (Symbolic Action Principle) — Lagrangian Meta-Framework.
Formalization of Euler-Lagrange trajectories for autonomous agents.

Common Currency: UAS (Unidades de Acción Simbólica).
Lagrangian: L_ψ = K_ψ (Kinetic/Gain) - S_ψ (Entropy/Cost) + G_grace - F_collapse
"""

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.evolution.psi_sap")


@dataclass
class PsiActionState:
    fitness: float
    entropy: float
    time_delta: float
    grace_constant: float = 1.0


def calculate_lagrangian(state: PsiActionState) -> float:
    """Calculates the L_ψ in UAS."""
    # K_ψ: Kinetic Energy (Velocity of Fitness gain per unit time)
    k_psi = state.fitness / max(0.001, state.time_delta)

    # S_ψ: Potential Energy (Entropy cost / Structural complexity)
    # Using a non-linear scaling to represent the logarithmic cost of information.
    s_psi = state.entropy * math.log(state.entropy + 1.1)

    # G_grace: Conservative Strategy Force (Injected potential)
    g_grace = state.grace_constant / (1.0 + state.entropy)

    return k_psi - s_psi + g_grace


# This will allow CORTEX to predict the "path of least symbolic action" for future
# improvements rather than relying purely on stochastic mutation.


class GeodesicPathfinder:
    """Predicts optimal mutation trajectories using Euler-Lagrange principles (Phase 3)."""

    def __init__(self, time_horizon: int = 5):
        self.time_horizon = time_horizon

    def calculate_action_integral(self, path: list[PsiActionState]) -> float:
        """Calculates total symbolic action S_ψ across a trajectory path."""
        s_total = 0.0
        for state in path:
            # S_ψ = ∫ L_ψ dt
            s_total += calculate_lagrangian(state) * state.time_delta
        return s_total

    def predict_optimal_mutation(
        self,
        current_state: PsiActionState,
        available_mutations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculates which mutation minimizes symbolic action over the local horizon.

        Args:
            current_state: The current UAS state.
            available_mutations: List of mutation payloads with predicted deltas.

        Returns:
            The mutation payload that satisfies the Euler-Lagrange stationary condition.
        """
        candidates = []
        for mut in available_mutations:
            # Simulate one step forward
            # K_ψ gain vs S_ψ entropic cost
            df = mut.get("delta_fitness", 0.0)
            de = mut.get("delta_entropy", 0.0)
            dt = mut.get("time_delta", 1.0)

            projected = PsiActionState(
                fitness=current_state.fitness + df,
                entropy=max(0.1, current_state.entropy + de),
                time_delta=dt,
            )

            l_val = calculate_lagrangian(projected)

            # We seek the stationary point of the action. In our UAS currency,
            # this aligns with maximizing the Lagrangian (Coherence over Chaos).
            candidates.append((l_val, mut))

        if not candidates:
            return {}

        # STATIONARY POINT: Argmax L_ψ (Least Action in UAS space)
        best_mut = max(candidates, key=lambda x: x[0])[1]
        logger.info(
            "🧬 [Ω₁] Geodesic path found: ΔFitness=%.2f, ΔEntropy=%.2f (L_ψ=%.2f UAS)",
            best_mut.get("delta_fitness", 0.0),
            best_mut.get("delta_entropy", 0.0),
            max(candidates, key=lambda x: x[0])[0],
        )
        return best_mut
