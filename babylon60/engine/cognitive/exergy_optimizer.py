# [C5-REAL] Exergy-Maximized
"""
Exergy Optimizer.
O(1) Heuristic Engine for Thermal utility and Swarm density.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.swarm.swarm_10k import NodeMetrics


class ExergyOptimizer:
    """Calculates crystalline exergy scores for Swarm nodes."""

    @staticmethod
    def calculate_node_exergy(
        metrics: NodeMetrics,
        latency_ms: float,
        max_capacity: int,
        latency_threshold: float = 16.0,
    ) -> float:
        """
        Calculate exergy (work potential) in O(1).
        Formula: Exergy = DensityFactor * LatencyFactor * UncertaintyPenalty
        """
        # Density Factor (Linear decay as capacity fills)
        density_factor = max(0.0, 1.0 - (metrics.active_children / float(max_capacity)))

        # Latency Factor (Exponential decay after threshold breach)
        # 16ms is the VOID-STATE threshold for human perception and JIT hardware.
        if latency_ms <= latency_threshold:
            latency_factor = 1.0
        else:
            # Rapid decay: factor = exp(-(latency - threshold) / decay_constant)
            latency_factor = math.exp(-(latency_ms - latency_threshold) / 32.0)

        # Uncertainty Penalty (Law Omega 1)
        uncertainty_penalty = 1.0 - metrics.uncertainty

        exergy = density_factor * latency_factor * uncertainty_penalty
        return max(0.0, min(1.0, exergy))

    @staticmethod
    def calculate_work_pressure(
        metrics: NodeMetrics,
        latency_ms: float,
    ) -> float:
        """
        Calculate the kinetic work pressure (saturation) in O(1).
        Pressure increases with both child density and latency breach.
        """
        # Density portion (0.0 to 1.0)
        density_p = metrics.active_children / 100.0 if metrics.active_children else 0.0

        # Latency portion (normalized against 16ms threshold)
        latency_p = min(1.0, latency_ms / 32.0) if latency_ms > 16.0 else 0.0

        # Combined pressure (weighted average)
        return (density_p * 0.4) + (latency_p * 0.6)

    @staticmethod
    def is_thermally_stable(exergy: float, threshold: float = 0.7) -> bool:
        """Trigger Dispatch block if exergy falls below threshold."""
        return exergy >= threshold

    @staticmethod
    def should_shard(exergy: float, threshold: float = 0.2) -> bool:
        """Trigger re-sharding if exergy collapse is detected."""
        return exergy < threshold
