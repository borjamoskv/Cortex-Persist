# [C5-REAL] Exergy-Maximized
import numpy as np

from cortex.simulation.primitives import MemoryTrajectory


class MemoryDriftDetector:
    """
    Detects if the system is 'dreaming too coherently' by measuring the KL divergence
    between the original intent distribution and the retrieved trajectory distribution.
    """

    @staticmethod
    def calculate_drift(base_intent_variance: float, trajectories: list[MemoryTrajectory]) -> float:
        """
        Approximates KL(real_distribution || retrieved_distribution).
        """
        if not trajectories:
            return 0.0

        # Variance of the retrieved paths (are they all collapsing to the exact same narrative?)
        scores = [t.total_score for t in trajectories]
        if len(scores) < 2:
            return 0.0

        retrieved_variance = np.var(scores)

        # If retrieved variance is suspiciously low compared to the intent variance, we are drifting into an elegant false memory.
        # Drift = log(base_var / retrieved_var)
        retrieved_variance = max(1e-6, retrieved_variance)
        base_intent_variance = max(1e-6, base_intent_variance)

        drift = np.log(base_intent_variance / retrieved_variance)

        return float(max(0.0, drift))
