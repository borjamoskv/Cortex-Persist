"""
CORTEX V5 - Temporal Inversion & Fluid Dynamics (PULMONES)
Visual/UI/UX: KAIROS-Ω, Fluid Dynamics, NotchLive integration.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil


@dataclass
class SpringConfig:
    mass: float = 1.0
    stiffness: float = 100.0
    damping: float = 10.0


class TemporalInversion:
    """
    KAIROS-Ω core logic. Calculating dynamic responses for interfaces so they
    don't just animate—they breathe and react to the user's velocity.
    """

    @staticmethod
    def calculate_spring_velocity(
        current: float, target: float, velocity: float, config: SpringConfig, delta_time: float
    ) -> tuple[float, float]:
        """
        Calculates the next position and velocity for a continuous spring animation.
        This provides the biological 'breathing' (PULMONES) feel required for
        Industrial Noir and NotchLive architectures.

        Formula: F = -k*x - c*v
        """
        # Displacement from target
        x = current - target

        # Spring force
        force = -config.stiffness * x - config.damping * velocity

        # Acceleration
        acceleration = force / config.mass

        # Integrate (Euler method)
        new_velocity = velocity + acceleration * delta_time
        new_position = current + new_velocity * delta_time

        # If very close to target with low velocity, snap to end (temporal optimization)
        if abs(new_position - target) < 0.001 and abs(new_velocity) < 0.001:
            return target, 0.0

        return new_position, new_velocity


class NotchFluidDynamics:
    """
    Simulates the non-linear fluid expansion of a dynamic UI element (like the Mac Notch).
    """

    @staticmethod
    def compute_notch_membrane(
        base_width: float, base_height: float, intensity: float
    ) -> tuple[float, float, float]:
        """
        Calculates the width, height, and corner radius of a membrane-like UI element
        expanding under abstract 'pressure' (intensity).
        """
        # Biological scaling based on KAIROS inversion principle.
        expansion = 1.0 + (math.log(1.0 + intensity) * 0.5)

        new_width = base_width * expansion
        new_height = base_height * (expansion**0.8)  # Non-linear dimension scaling

        # The more it stretches, the more fluid the corner radius becomes
        corner_radius = min(new_width, new_height) * 0.5

        return new_width, new_height, corner_radius


class SystemRespiration:
    """
    KAIROS-Ω physical integration (PULMONES).
    Determines how 'deeply' the background system should breathe (execute).
    If the human is active or load is high, it yields (shallow breath).
    If the system is idle or during maintenance hours, it expands (deep breath).
    """

    @staticmethod
    def get_current_state() -> tuple[float, int, bool]:
        """
        Returns:
            throttle_multiplier (float): 1.0 (normal) to 5.0 (slowed down).
            swarm_size_limit (int): Max agents to spawn (e.g. 5 up to 50).
            ok_to_run (bool): False if CPU load is critically high.
        """
        now = datetime.now(timezone.utc)
        cpu_percent = psutil.cpu_percent(interval=None)

        if cpu_percent > 85.0:
            # Critical load: choke background tasks
            return 5.0, 3, False

        # 03:00 to 05:00 is deep maintenance window
        if 3 <= now.hour < 5:
            return 0.5, 50, True

        # Working hours (09:00 to 19:00) throttle back
        if 9 <= now.hour <= 19:
            throttle = 2.0 if cpu_percent > 40 else 1.0
            return throttle, 10, True

        # Evening / Night
        return 1.0, 20, True
