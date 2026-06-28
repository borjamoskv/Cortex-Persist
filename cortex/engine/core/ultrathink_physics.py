# [C5-REAL] Exergy-Maximized
"""
Motor de Física Termodinámica para el modo Ultrathink (P0-Mechanics).
Calcula la exergía cognitiva y el Blast Radius para autorizar bifurcaciones masivas.
"""

import logging
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("cortex.engine.exergy_physics")

class LegionFormation(str, Enum):
    """Sovereign Swarm Formations (LEGIØN-1 Protocol)"""
    HYDRA = "HYDRA"         # 10-20 agents: Parallel domain mutation
    PHOENIX = "PHOENIX"     # 5-8 agents: Self-healing & technical debt
    LEVIATHAN = "LEVIATHAN" # 20-50 agents: Total P0 singularity siege
    ORACLE = "ORACLE"       # 3-5 agents: Strategic prediction
    OUROBOROS = "OUROBOROS" # 3-7 agents: Recursive self-improvement
    TESTUDO = "TESTUDO"     # 15 agents: Proactive infrastructure defense

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
    def calculate_legion_formation(epicenter_radius: int, exergy_yield: float) -> LegionFormation:
        """
        Collapses thermodynamic requirements into a specific LEGIØN-1 Swarm Formation.
        """
        if epicenter_radius >= 10 and exergy_yield > (UltrathinkPhysicsEngine.SINGULARITY_CONSTANT * 0.5):
            return LegionFormation.LEVIATHAN
        if epicenter_radius >= 7:
            return LegionFormation.HYDRA
        if epicenter_radius >= 5:
            return LegionFormation.TESTUDO
        if exergy_yield > (UltrathinkPhysicsEngine.SINGULARITY_CONSTANT * 0.3):
            return LegionFormation.OUROBOROS
        return LegionFormation.PHOENIX

    @staticmethod
    def authorize_ultrathink(
        stochastic_entropy: float,
        deterministic_output: float,
        execution_time: float,
        epicenter_radius: int,
    ) -> tuple[bool, str, Optional[LegionFormation]]:
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
                None
            )

        if exergy < (UltrathinkPhysicsEngine.SINGULARITY_CONSTANT * 0.1):
            return (
                False, 
                f"Insufficient Exergy Yield ({exergy:.2f}) for JIT structural collapse.",
                None
            )

        formation = UltrathinkPhysicsEngine.calculate_legion_formation(epicenter_radius, exergy)
        return True, f"Ultrathink P0 Singularity Horizon Authorized. Swarm: {formation.value}", formation
