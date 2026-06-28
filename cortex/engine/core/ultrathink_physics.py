# [C5-REAL] Exergy-Maximized
"""
Motor de Física Termodinámica para el modo Ultrathink (P0-Mechanics).
Calcula la exergía cognitiva y el Blast Radius para autorizar bifurcaciones masivas.
"""

import logging
from typing import Any

logger = logging.getLogger("cortex.engine.exergy_physics")


class UltrathinkPhysicsEngine:
    """
    Controlador matemático para la Inferencia P0.
    Aplica la fórmula de Exergía Cognitiva.
    """

    # Constante de Singularidad (Singularity Exergy Limit)
    SINGULARITY_CONSTANT: float = 100.0

    @staticmethod
    def calculate_exergy_yield(
        stochastic_entropy: float, deterministic_output: float, execution_time: float
    ) -> float:
        """
        Calcula la exergía (Ξ) producida en un ciclo de razonamiento.
        Ξ = (S_out[Determinista] - S_in[Estocástico]) / ΔT
        """
        if execution_time <= 0:
            return 0.0

        exergy = (deterministic_output - stochastic_entropy) / execution_time
        return max(0.0, exergy)

    @staticmethod
    def measure_blast_radius(dependency_graph: dict[str, Any], epicenter_node: str) -> int:
        """
        Calcula el 'Blast Radius' topológico de una corrupción P0 para el aislamiento térmico.
        Devuelve el número de niveles y ramificaciones afectadas.
        """
        visited = set()
        queue = [epicenter_node]

        while queue:
            current = queue.pop(0)
            if current not in visited:
                visited.add(current)
                if current in dependency_graph:
                    neighbors = dependency_graph[current]
                    if isinstance(neighbors, list):
                        queue.extend([n for n in neighbors if n not in visited])
                    elif isinstance(neighbors, dict):
                        queue.extend([n for n in neighbors.keys() if n not in visited])

        # The Blast Radius is the size of the affected cluster
        radius = len(visited)
        logger.debug("Blast Radius measure for %s: %d", epicenter_node, radius)
        return radius

    @staticmethod
    def authorize_ultrathink(
        stochastic_entropy: float,
        deterministic_output: float,
        execution_time: float,
        epicenter_radius: int,
    ) -> tuple[bool, str]:
        """
        El colapso a 'Ultrathink' exige un rendimiento exergético masivo
        y un radio de explosión demostrable.
        """
        exergy = UltrathinkPhysicsEngine.calculate_exergy_yield(
            stochastic_entropy, deterministic_output, execution_time
        )

        if epicenter_radius < 3:
            return (
                False,
                f"Blast radius ({epicenter_radius}) too small for Ultrathink. Use Deep Think.",
            )

        if exergy < (UltrathinkPhysicsEngine.SINGULARITY_CONSTANT * 0.1):
            return False, f"Insufficient Exergy Yield ({exergy:.2f}) for JIT structural collapse."

        return True, "Ultrathink P0 Singularity Horizon Authorized."
