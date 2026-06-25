# [C5-REAL] Exergy-Maximized
import random
from typing import Any

import numpy as np

from legacy_research.observability.fdf import FailureField, Particle


def memory_entropy(history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    diffs = np.diff(history)
    return float(np.var(diffs) + np.mean(np.abs(diffs)))


def lagrangian(task: Particle, state_vec: np.ndarray, meta: Any, field: FailureField) -> float:
    # T: Useful energy (exergy gain)
    T = task.original_stats.exergy_mean

    # V: Failure potential
    V = float(field.potential(task.position)) if field.fitted else 0.0

    # H: Accumulated memory entropy
    H = memory_entropy(task.history)

    # R: Structural risk (variance)
    R = meta.alpha_risk * task.original_stats.exergy_var

    # Lagrangian density: T - V - R - H
    return float(T - V - R - H)


def action(
    trajectory: list[Particle], state_vec: np.ndarray, meta: Any, field: FailureField
) -> float:
    S = 0.0
    for t in trajectory:
        L = lagrangian(t, state_vec, meta, field)
        dt = (
            t.original_stats.runtime_mean
            if getattr(t.original_stats, "runtime_mean", 0) > 0
            else 1.0
        )
        # Mínima acción clásica minimiza (V - T), es decir, maximiza (T - V).
        # Aquí L es (T - V - R - H). Queremos MAXIMIZAR L, por tanto la Acción (coste) a minimizar es -L * dt
        S += -L * dt
    return S


def sample_trajectories(
    tasks: list[Particle], horizon: int = 5, num_samples: int = 50
) -> list[list[Particle]]:
    if not tasks:
        return []

    trajectories = []
    path_len = min(horizon, len(tasks))

    for _ in range(num_samples):
        # Muestreo sin reemplazo (un workflow se ejecuta una vez por path)
        path = random.sample(tasks, path_len)
        trajectories.append(path)

    return trajectories


def select_next(
    tasks: list[Particle],
    state_vec: np.ndarray,
    field: FailureField,
    meta: Any,
    horizon: int = 5,
    epsilon: float = 0.1,
) -> list[Particle]:
    best_score = float("inf")

    trajectories = sample_trajectories(tasks, horizon=horizon, num_samples=100)

    # Path score tuples for ranking
    scored_paths = []

    for path in trajectories:
        S = action(path, state_vec, meta, field)
        scored_paths.append((S, path))

        if best_score > S:
            best_score = S

    # Epsilon Path Noise: Evitar Global Path Bias Collapse
    if random.random() < epsilon and scored_paths:
        # Escoge un path aleatorio entre el top 30% para inyectar entropía
        top_k = max(1, int(len(scored_paths) * 0.3))
        scored_paths.sort(key=lambda x: x[0])
        chosen = random.choice(scored_paths[:top_k])
        chosen[1]
        best_score = chosen[0]

    # Return sorted individual tasks based on their best action contribution?
    # No, we just sort the candidate tasks by their *individual* action cost in the best path,
    # or just sort them globally by their individual action to maintain API compatibility.

    # Para el scheduler de CORTEX que espera una lista ordenada:
    # Ordenamos todas las tareas por su "coste de acción individual"
    # Action cost = -L * dt
    scored_tasks = []
    for t in tasks:
        L = lagrangian(t, state_vec, meta, field)
        dt = (
            t.original_stats.runtime_mean
            if getattr(t.original_stats, "runtime_mean", 0) > 0
            else 1.0
        )
        cost = -L * dt
        scored_tasks.append((cost, t))

    scored_tasks.sort(key=lambda x: x[0])
    return [t for _, t in scored_tasks]
