# [C5-REAL] Exergy-Maximized
from cortex.simulation.primitives import MemoryTrajectory, SimulationField

from cortex.simulation.drift_detector import MemoryDriftDetector
from cortex.simulation.thermodynamics import MemoryEnergyField


class MemoryCollapseProtocol:
    """
    Evaluates trajectories and decides whether to collapse into a single narrative
    or maintain superposition, strictly bound by thermodynamic budget.
    """

    def __init__(self, energy_budget: float = 100.0, drift_epsilon: float = 0.5):
        self.energy_budget = energy_budget
        self.epsilon_low = drift_epsilon

    def evaluate(
        self, trajectories: list[MemoryTrajectory], base_intent_variance: float = 0.05
    ) -> SimulationField:
        if not trajectories:
            return SimulationField(trajectories=[], is_collapsed=True, mode="EXTRACTIVE_MODE")

        trajectories.sort(key=lambda x: x.total_score, reverse=True)
        top_traj = trajectories[0]

        # 1. Memory Drift Detection
        drift = MemoryDriftDetector.calculate_drift(base_intent_variance, trajectories)

        # 2. Thermodynamic Evaluation
        thermo_state = MemoryEnergyField.compute_energy(trajectories, drift, self.energy_budget)

        # 3. Collapse Decision based on Budget
        # if total_energy > budget: force_collapse()
        if thermo_state.total_energy > thermo_state.energy_budget:
            # Cannot afford superposition, forces extractive collapse
            return SimulationField(
                trajectories=[top_traj],
                is_collapsed=True,
                mode="EXTRACTIVE_MODE_BUDGET_COLLAPSE",
                dominant_trajectory=top_traj,
            )

        if drift < self.epsilon_low and top_traj.coherence_score > 0.9:
            # Trigger anti-hallucination noise (force superposition to prevent false memory)
            return SimulationField(
                trajectories=trajectories[:5],  # Keep top 5 in superposition
                is_collapsed=False,
                mode="SUPERPOSITION_MODE_DRIFT_PREVENTION",
            )

        # 4. Phase-based fallback
        if thermo_state.phase == "SOLID":
            return SimulationField(
                trajectories=[top_traj],
                is_collapsed=True,
                mode="EXTRACTIVE_MODE",
                dominant_trajectory=top_traj,
            )
        else:
            # LIQUID or PLASMA -> Superposition
            return SimulationField(
                trajectories=trajectories[:10],
                is_collapsed=False,
                mode=f"SUPERPOSITION_MODE_{thermo_state.phase}",
            )
