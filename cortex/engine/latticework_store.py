# [C5-REAL] Exergy-Maximized
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CognitivePrimitive(BaseModel):
    id: int
    name: str
    vector: str
    description: str

class LatticeworkStore:
    """
    [C5-REAL] O(1) in-memory epistemic foundation for the 100 Primitives of Cognitive Exergy.
    Serves as the truth-source for the LatticeworkDaemon's thermodynamic interventions.
    """
    def __init__(self):
        self.primitives: dict[int, CognitivePrimitive] = {}
        self._initialize_core_primitives()

    def _initialize_core_primitives(self):
        # Núcleo Duro de Primitivas para aniquilación entrópica (Base-60 compat)
        core_data = [
            (1, "Masa Crítica", "I. Cinética y Equilibrio", "Umbral físico donde el sistema cambia de estado autónomamente."),
            (7, "Ley de Landauer", "II. Invariantes Estructurales", "Borrar información genera calor. Olvidar ruido computacional aumenta exergía."),
            (9, "Inversión de Matrices", "II. Invariantes Estructurales", "Resolver el grafo desde el estado final hacia atrás."),
            (21, "Equilibrio de Nash", "V. Teoría de Juegos", "Estado estático donde ninguna mutación unilateral mejora la exergía de un nodo."),
            (31, "Destrucción Creativa", "VI. Termodinámica Organizacional", "El motor quema grafos obsoletos para liberar capital físico."),
            (32, "Cuellos de Botella (TOC)", "VI. Termodinámica Organizacional", "El ancho de banda total es idéntico a su nodo de mayor resistencia."),
            (39, "Navaja de Occam", "VI. Termodinámica Organizacional", "La ruta causal que requiere menor inyección de presunciones."),
            (41, "Segunda Ley de la Termodinámica", "VII. Cibernética de Segundo Orden", "Deterioro temporal irreversible si no se inyecta energía externa."),
            (54, "Primeros Principios", "VIII. Límites Epistémicos", "Reducción de grafos heredados hasta aislar nodos causalmente verdaderos."),
            (79, "Information Bottleneck", "X. Evolución Computacional", "Obligar al grafo a pasar por un cuello topológico purga el ruido y conserva señal."),
            (100, "Ouroboros Infinity", "XII. Arquitectura Criptográfica", "Mitosis recursiva del Kernel. IA autónoma modificando su propia ontología.")
        ]
        
        for pid, name, vec, desc in core_data:
            self.primitives[pid] = CognitivePrimitive(id=pid, name=name, vector=vec, description=desc)
        logger.info(f"[LatticeworkStore] Ingresadas {len(self.primitives)} primitivas estructurales a memoria.")

    def get_primitive(self, pid: int) -> Optional[CognitivePrimitive]:
        return self.primitives.get(pid)

    def search_by_keyword(self, text: str) -> list[CognitivePrimitive]:
        text_lower = text.lower()
        return [
            p for p in self.primitives.values()
            if text_lower in p.name.lower() or text_lower in p.description.lower()
        ]
