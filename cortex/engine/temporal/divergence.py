# [C5-REAL] Exergy-Maximized
"""
Temporal Divergence & State Distance Metric.

Computes the geometric distance between two execution trajectories.
Identifies execution drift and calculates StateDistance.
"""

import difflib
from typing import Any


class DivergenceMap:
    """
    Geometric distance calculator for execution trajectories.
    Treats an execution trace as a sequence of discrete actions in a metric space.
    """

    @staticmethod
    def compute_distance(trajectory_a: list[dict[str, Any]], trajectory_b: list[dict[str, Any]]) -> float:
        """
        Computes the structural distance between two execution trajectories.
        Returns a normalized score where 0.0 is identical and 1.0 is completely divergent.
        """
        # We extract the sequence of actions as the primary structural dimension
        seq_a = [str(node.get("action", "")) for node in trajectory_a]
        seq_b = [str(node.get("action", "")) for node in trajectory_b]

        if not seq_a and not seq_b:
            return 0.0
        
        # SequenceMatcher ratio returns 1.0 for identical sequences, 0.0 for completely different
        ratio = difflib.SequenceMatcher(None, seq_a, seq_b).ratio()
        
        # We want distance, so 1.0 - ratio
        return 1.0 - ratio

    @staticmethod
    def analyze_divergence(trajectory_a: list[dict[str, Any]], trajectory_b: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Provides a detailed map of where two trajectories diverge.
        """
        seq_a = [str(node.get("action", "")) for node in trajectory_a]
        seq_b = [str(node.get("action", "")) for node in trajectory_b]
        
        divergence_point = -1
        for i, (a, b) in enumerate(zip(seq_a, seq_b)):
            if a != b:
                divergence_point = i
                break
                
        if divergence_point == -1 and len(seq_a) != len(seq_b):
            divergence_point = min(len(seq_a), len(seq_b))
            
        return {
            "is_identical": seq_a == seq_b,
            "state_distance": DivergenceMap.compute_distance(trajectory_a, trajectory_b),
            "divergence_point": divergence_point,
            "trajectory_a_len": len(seq_a),
            "trajectory_b_len": len(seq_b),
        }
