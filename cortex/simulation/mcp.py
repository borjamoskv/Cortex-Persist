import numpy as np
from typing import List, Optional
from cortex.simulation.primitives import MemoryTrajectory, SimulationField
from cortex.simulation.drift_detector import MemoryDriftDetector

class MemoryCollapseProtocol:
    """
    Evaluates trajectories and decides whether to collapse into a single narrative
    or maintain superposition.
    """
    def __init__(self, entropy_threshold: float = 1.5, drift_epsilon: float = 0.5):
        self.theta_high = entropy_threshold
        self.epsilon_low = drift_epsilon
        
    def evaluate(self, trajectories: List[MemoryTrajectory], base_intent_variance: float = 0.05) -> SimulationField:
        if not trajectories:
            return SimulationField(trajectories=[], is_collapsed=True, mode="EXTRACTIVE_MODE")
            
        # 1. Entropy Spike Detection
        graph_entropy = np.mean([t.entropy_penalty for t in trajectories])
        
        # 2. Stability Evaluation (Score trajectories)
        for t in trajectories:
            # Re-evaluate coherence at trajectory level if needed, for now use total_score
            pass
            
        trajectories.sort(key=lambda x: x.total_score, reverse=True)
        top_traj = trajectories[0]
        
        # 3. Memory Drift Detection (Dreaming too coherently?)
        drift = MemoryDriftDetector.calculate_drift(base_intent_variance, trajectories)
        
        if drift < self.epsilon_low and top_traj.coherence_score > 0.9:
            # Trigger anti-hallucination noise (force superposition to prevent false memory)
            return SimulationField(
                trajectories=trajectories[:5], # Keep top 5 in superposition
                is_collapsed=False,
                mode="SUPERPOSITION_MODE_DRIFT_PREVENTION"
            )
            
        # 4. Collapse Decision
        if graph_entropy > self.theta_high:
            # Enter superposition due to high uncertainty
            return SimulationField(
                trajectories=trajectories[:10], # Keep top 10
                is_collapsed=False,
                mode="SUPERPOSITION_MODE"
            )
        else:
            # Extractive collapse
            return SimulationField(
                trajectories=[top_traj],
                is_collapsed=True,
                mode="EXTRACTIVE_MODE",
                dominant_trajectory=top_traj
            )
