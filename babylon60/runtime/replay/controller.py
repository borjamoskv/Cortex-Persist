# [C5-REAL] Exergy-Maximized
"""
Temporal Consistency Controller

Convierte el DivergenceMap de un sensor pasivo a un sistema de control activo.
Regula el runtime de 3 formas:
1. Clamp Entropy: Frena ramas de ejecución cuya complejidad crece descontroladamente.
2. Enforce Attractor: Fuerza a la ejecución a no separarse más de L-distance de un baseline.
3. Strict Determinism: Modo CI gate incrustado en runtime (cero tolerancia a divergencia).
"""

from __future__ import annotations

from typing import Any

from babylon60.runtime.replay.divergence import DivergenceMap, DivergenceReport


class EntropyViolation(Exception):
    """Lanzada cuando el gradiente de entropía excede el límite permitido."""


class AttractorViolation(Exception):
    """Lanzada cuando la distancia a la trayectoria base excede el límite permitido."""


class TemporalConsistencyController:
    """Nervioso sistema del runtime: regula la historia de ejecución."""

    def __init__(self, baseline_trajectory: list[dict[str, Any]] | None = None):
        """
        :param baseline_trajectory: Trayectoria 'attractor' de referencia.
        """
        self.baseline = baseline_trajectory or []
        self._entropy_threshold: float | None = None
        self._distance_threshold: float | None = None

    def clamp_entropy(self, max_mean_gradient: float) -> TemporalConsistencyController:
        """Activa control de entropía: rechaza trayectorias con complejidad descontrolada."""
        self._entropy_threshold = max_mean_gradient
        return self

    def enforce_attractor(self, max_distance: float) -> TemporalConsistencyController:
        """Fuerza que la ejecución no diverja más que `max_distance` de la baseline."""
        self._distance_threshold = max_distance
        return self

    def enforce_strict_determinism(self) -> TemporalConsistencyController:
        """Alias para enforce_attractor(0.0)."""
        return self.enforce_attractor(0.0)

    def regulate(self, current_trajectory: list[dict[str, Any]]) -> DivergenceReport:
        """
        Evalúa la trayectoria actual contra las reglas del controlador.
        Lanza excepciones si se violan las leyes termodinámicas de la máquina.
        Retorna el reporte de divergencia si es válido.
        """
        # 1. Si no hay baseline, solo evaluamos entropía del current
        if not self.baseline:
            report = DivergenceMap([current_trajectory, current_trajectory]).analyze()
        else:
            report = DivergenceMap([self.baseline, current_trajectory]).analyze()

        # 2. Control de Entropía
        if self._entropy_threshold is not None:
            # Revisamos la deriva de la trayectoria actual (que es el índice 0 o 1 dependiendo de baseline)
            idx = 1 if self.baseline else 0
            current_drift = next(
                (d for d in report.entropy_drifts if d.trajectory_index == idx), None
            )

            if current_drift and current_drift.mean_gradient > self._entropy_threshold:
                raise EntropyViolation(
                    f"[ENTROPY VIOLATION] Gradient {current_drift.mean_gradient:.4f} "
                    f"exceeds max {self._entropy_threshold:.4f}"
                )

        # 3. Control de Distancia (Attractor)
        if self._distance_threshold is not None and self.baseline:
            if report.max_distance > self._distance_threshold:
                raise AttractorViolation(
                    f"[ATTRACTOR VIOLATION] Max distance {report.max_distance:.4f} "
                    f"exceeds tolerance {self._distance_threshold:.4f}"
                )

        return report
