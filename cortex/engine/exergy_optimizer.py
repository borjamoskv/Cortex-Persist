# [C5-REAL] Exergy-Maximized
"""
Exergy Optimizer.
O(1) Heuristic Engine for Thermal utility and Swarm density.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from cortex.engine.babylon60 import Babylon60

if TYPE_CHECKING:
    from cortex.engine.swarm_10k import NodeMetrics


class ExergyOptimizer:
    """Calculates crystalline exergy scores for Swarm nodes using BABYLON-60 Epistemology."""

    @staticmethod
    def calculate_node_exergy(
        metrics: NodeMetrics,
        latency_ms: Babylon60,
        max_capacity: int,
        latency_threshold: Babylon60 = Babylon60(16.0),
    ) -> Babylon60:
        """
        Calculate exergy (work potential) in O(1) deterministically.
        Formula: Exergy = DensityFactor * LatencyFactor * UncertaintyPenalty
        """
        b60_one = Babylon60.from_raw(Babylon60.SCALE)
        b60_zero = Babylon60.from_raw(0)

        # Density Factor (Linear decay as capacity fills)
        cap_b60 = Babylon60(max_capacity)
        active_b60 = Babylon60(metrics.active_children)
        
        # density_factor = max(0, 1 - (active / capacity))
        if active_b60 >= cap_b60:
            density_factor = b60_zero
        else:
            density_factor = b60_one - (active_b60 / cap_b60)

        # Latency Factor (Linear decay in Babylon60 to replace math.exp)
        # VOID-STATE threshold is 16ms
        if latency_ms <= latency_threshold:
            latency_factor = b60_one
        else:
            # Linear decay: factor = 1 - (latency - threshold) / 32
            diff = latency_ms - latency_threshold
            decay_b60 = Babylon60(32.0)
            decay_term = diff / decay_b60
            
            if decay_term >= b60_one:
                latency_factor = b60_zero
            else:
                latency_factor = b60_one - decay_term

        # Uncertainty Penalty (Law Omega 1)
        uncertainty_penalty = b60_one - metrics.uncertainty

        exergy = density_factor * latency_factor * uncertainty_penalty
        
        if exergy < b60_zero:
            return b60_zero
        if exergy > b60_one:
            return b60_one
        return exergy

    @staticmethod
    def calculate_work_pressure(
        metrics: NodeMetrics,
        latency_ms: Babylon60,
    ) -> Babylon60:
        """
        Calculate the kinetic work pressure (saturation) in O(1).
        """
        b60_one = Babylon60.from_raw(Babylon60.SCALE)
        b60_zero = Babylon60.from_raw(0)

        # Density portion (0.0 to 1.0)
        active_b60 = Babylon60(metrics.active_children)
        hundred_b60 = Babylon60(100)
        if metrics.active_children > 0:
            density_p = active_b60 / hundred_b60
        else:
            density_p = b60_zero

        # Latency portion (normalized against 16ms threshold -> 32ms)
        threshold_b60 = Babylon60(16.0)
        thirty_two_b60 = Babylon60(32.0)
        if latency_ms > threshold_b60:
            latency_p = latency_ms / thirty_two_b60
            if latency_p > b60_one:
                latency_p = b60_one
        else:
            latency_p = b60_zero

        # Combined pressure (weighted average: 40% density, 60% latency)
        w_density = Babylon60(0.4)
        w_latency = Babylon60(0.6)
        return (density_p * w_density) + (latency_p * w_latency)

    @staticmethod
    def is_thermally_stable(exergy: Babylon60, threshold: Babylon60 = Babylon60(0.7)) -> bool:
        """Trigger Dispatch block if exergy falls below threshold."""
        return exergy >= threshold

    @staticmethod
    def should_shard(exergy: Babylon60, threshold: Babylon60 = Babylon60(0.2)) -> bool:
        """Trigger re-sharding if exergy collapse is detected."""
        return exergy < threshold
