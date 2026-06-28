# [C5-REAL] Exergy-Maximized
"""
MetaArbiter & EntropyDrift.

Topological collapse operator. Analyzes multiple execution trajectories
and selects the canonical path (the one with the lowest EntropyDrift).
"""

from typing import Any

from cortex.engine.temporal.divergence import DivergenceMap


class MetaArbiter:
    """
    Arbitrates conflict in parallel swarm execution by collapsing topologies.
    """

    @staticmethod
    def compute_entropy_drift(trajectory: list[dict[str, Any]], reference_trajectory: list[dict[str, Any]]) -> float:
        """
        Computes the EntropyDrift of a trajectory against a reference (or expected) trajectory.
        Higher drift means it diverges more from the expected state space.
        """
        # Calculate StateDistance
        distance = DivergenceMap.compute_distance(trajectory, reference_trajectory)
        
        # In a more advanced implementation, we would also factor in time variance,
        # resource mutations, and LLM perplexity.
        
        return distance

    @staticmethod
    def collapse_topology(trajectories: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """
        Given multiple parallel execution trajectories, returns the one with the lowest entropy.
        If all trajectories are identical, returns the first one.
        """
        if not trajectories:
            return []
            
        if len(trajectories) == 1:
            return trajectories[0]

        # Calculate pairwise distances to find the 'consensus' trajectory.
        # The trajectory with the lowest average distance to all others is the canonical one.
        drift_scores = []
        for i, candidate in enumerate(trajectories):
            total_distance = 0.0
            for j, reference in enumerate(trajectories):
                if i != j:
                    total_distance += DivergenceMap.compute_distance(candidate, reference)
            
            avg_drift = total_distance / (len(trajectories) - 1)
            drift_scores.append((avg_drift, candidate))
            
        # Sort by lowest average drift
        drift_scores.sort(key=lambda x: x[0])
        
        # Return the one with the lowest drift (highest consensus)
        canonical_trajectory = drift_scores[0][1]
        
        return canonical_trajectory
