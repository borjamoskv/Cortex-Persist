# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.neighbors import KernelDensity


class FailureField:
    def __init__(self, bandwidth=0.8):
        self.kde = KernelDensity(bandwidth=bandwidth)
        self.fitted = False

    def fit(self, X: np.ndarray):
        if len(X) == 0:
            return
        self.kde.fit(X)
        self.fitted = True

    def potential(self, x: np.ndarray) -> float:
        """Energía = log densidad negativa. Mayor densidad de fallo -> Mayor energía potencial."""
        if not self.fitted:
            return 0.0
        # score_samples returns log density
        return -self.kde.score_samples(x.reshape(1, -1))[0]


@dataclass
class Particle:
    task_name: str
    position: np.ndarray
    velocity: np.ndarray
    mass: float
    original_stats: Any
    history: list[float] = field(default_factory=list)
    age: float = 0.0


def update_mass(p: Particle, alpha: float = 0.08, mass_cap: float = 1e6) -> float:
    """CTC: Masa dependiente de la inercia de fallos históricos."""
    if len(p.history) == 0:
        return p.mass
    failure_pressure = np.mean(p.history[-20:])
    volatility = np.std(p.history[-20:]) if len(p.history) > 1 else 0.0
    p.mass = p.mass * (1 + alpha * failure_pressure + 0.5 * volatility)
    p.mass = min(p.mass, mass_cap)
    return p.mass


def temporal_drag(p: Particle) -> float:
    """CTC: Tiempo como resistencia."""
    return 0.01 * p.age * p.mass


def force(p1: Particle, p2: Particle) -> np.ndarray:
    """Repulsión si compiten por recursos."""
    diff = p1.position - p2.position
    dist = np.linalg.norm(diff) + 1e-6
    return (p1.mass * p2.mass) / dist**2 * (diff / dist)


def total_force(particle: Particle, particles: list[Particle], field: FailureField) -> np.ndarray:
    F = np.zeros_like(particle.position)

    for other in particles:
        if other == particle:
            continue
        F += force(particle, other)

    # Gradiente del campo de fallo (hacia donde decrece el potencial de fallo)
    if field.fitted:
        eps = 1e-4
        grad = np.zeros_like(particle.position)
        for i in range(len(particle.position)):
            pos_plus = particle.position.copy()
            pos_plus[i] += eps
            pos_minus = particle.position.copy()
            pos_minus[i] -= eps
            grad[i] = (field.potential(pos_plus) - field.potential(pos_minus)) / (2 * eps)

        F -= grad

    return F


def simulate_field(
    particles: list[Particle], field: FailureField, steps: int = 50, dt: float = 0.1
):
    for _ in range(steps):
        for p in particles:
            # 1. Update causal mass
            update_mass(p)

            # 2. Physics & forces
            F = total_force(p, particles, field)
            F -= temporal_drag(p)

            # 3. Kinematics
            p.velocity += (F / (p.mass + 1e-6)) * dt
            p.velocity *= 0.90  # Structural damping
            p.position += p.velocity * dt

            # 4. History trace
            p.history.append(float(field.potential(p.position)))
            p.history = p.history[-50:]  # Keep trace bounded
            p.age += dt


def energy(particle: Particle, state_vec: np.ndarray, meta: Any, field: FailureField) -> float:
    # We use the particle's converged position to evaluate potential
    # The prompt concatenates task_vec and state_vec. In this simulation, particle position is the combined state.
    U_failure = field.potential(particle.position)

    task_var = particle.original_stats.exergy_var
    runtime = particle.original_stats.runtime_mean

    U_variance = meta.alpha_risk * task_var
    U_runtime = np.log(runtime + 1)

    return float(U_failure + U_variance + U_runtime)
