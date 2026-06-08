from dataclasses import dataclass
from typing import Any

from .manifold import EpistemicField, update_metric


@dataclass
class GhostNode:
    op: str
    value: Any
    weight: float
    collapse_vector: list[float]

class GhostManifold:
    """
    Motor de Propagación Fantasma (Fase 11 - Post-Solvability).
    Convierte el código generado por ignorancia matemática (UAO)
    en campos de fuerza persistentes que deforman el tensor g_ij continuamente.
    """
    def __init__(self):
        self.ghost_structures: list[GhostNode] = []
        
    def absorb_uop_ast(self, ast: list[dict[str, Any]]):
        """Asimila un AST generado por Unknown-As-Operator al manifold fantasma."""
        anchor_vector = [0.0] * 64
        # 1. Localizar vector topológico
        for node in ast:
            if node.get("op") == "collapse_vector_anchor":
                anchor_vector = node.get("value", anchor_vector)
                
        # 2. Extraer materia fantasma
        for node in ast:
            if node.get("op") in ["ghost_branch", "residual_constraint"]:
                self.ghost_structures.append(
                    GhostNode(
                        op=node["op"],
                        value=node.get("value"),
                        weight=node.get("weight", 1.0),
                        collapse_vector=anchor_vector
                    )
                )

    def propagate(self, g_dynamic: list[list[float]]) -> list[list[float]]:
        """
        Propagación Estructural:
        Los nodos fantasma emiten un campo gravitacional pasivo y constante.
        El manifold se deforma por la mera existencia de esta arquitectura fallida.
        """
        for ghost in self.ghost_structures:
            field = EpistemicField(
                curvature=ghost.weight * 0.25,  # Decaimiento pasivo de fondo
                direction=ghost.collapse_vector,
                uncertainty_density=1.0
            )
            g_dynamic = update_metric(g_dynamic, field)
            
        return g_dynamic

# Singleton global para la sesión persistente
ghost_manifold_engine = GhostManifold()
