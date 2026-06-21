# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass

import numpy as np

from cortex.simulation.primitives import MemoryTrajectory


@dataclass
class ThermodynamicState:
    global_temperature: float
    phase: str  # SOLID, LIQUID, PLASMA
    total_energy: float
    energy_budget: float


class MemoryFrictionEngine:
    """
    Computes entropic friction for traversing graph edges.
    F = λ1 * hop_distance + λ2 * semantic_divergence + λ3 * temporal_gap
    """

    def __init__(self, lambda1: float = 0.5, lambda2: float = 2.0, lambda3: float = 0.1):
        self.L1 = lambda1
        self.L2 = lambda2
        self.L3 = lambda3

    def compute_friction(
        self, hop_distance: int, semantic_similarity: float, temporal_gap: float
    ) -> float:
        semantic_divergence = max(0.0, 1.0 - semantic_similarity)
        # Normalizing temporal gap heuristics
        gap_penalty = min(temporal_gap / 86400.0, 10.0) if temporal_gap > 0 else 0.0

        f = (self.L1 * hop_distance) + (self.L2 * semantic_divergence) + (self.L3 * gap_penalty)
        return float(f)


class MemoryEnergyField:
    """
    E(memory_state) = E_retrieval + E_coherence + E_drift + E_graph_traversal
    """

    @staticmethod
    def compute_energy(
        trajectories: list[MemoryTrajectory], drift: float, base_budget: float = 100.0
    ) -> ThermodynamicState:
        if not trajectories:
            return ThermodynamicState(
                global_temperature=0.0, phase="SOLID", total_energy=0.0, energy_budget=base_budget
            )

        N = len(trajectories)

        # Superposition tax: energy_cost = k * log(number_of_trajectories)
        k_tax = 5.0
        e_superposition = k_tax * np.log(max(1, N))

        # E_graph_traversal (accumulated friction/entropy)
        e_traversal = np.sum([np.mean([p.entropy for p in t.particles]) for t in trajectories])

        # E_coherence (lack of coherence costs energy)
        avg_coherence = np.mean([t.coherence_score for t in trajectories])
        e_incoherence = max(0.0, (1.0 - avg_coherence)) * 20.0

        # E_drift (hallucination penalty)
        e_drift = drift * 50.0

        total_energy = e_superposition + e_traversal + e_incoherence + e_drift

        # Calculate Memory Temperature
        # T_memory = f(user_intent_entropy, graph_entropy, drift_level)
        graph_entropy = np.mean([t.entropy_penalty for t in trajectories])
        t_memory = float(graph_entropy + (drift * 2.0))

        # Phase Transitions
        if t_memory < 0.5:
            phase = "SOLID"
        elif t_memory < 2.0:
            phase = "LIQUID"
        else:
            phase = "PLASMA"

        return ThermodynamicState(
            global_temperature=t_memory,
            phase=phase,
            total_energy=float(total_energy),
            energy_budget=base_budget,
        )
