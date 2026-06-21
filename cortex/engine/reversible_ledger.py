import time
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class EpistemicDelta:
    """Un Delta reversible, análogo a una puerta Toffoli lógica en el Ledger."""
    fact_id: str
    action: str  # "ASSERT" o "INVERT"
    content: str
    timestamp: float
    causal_parent: Optional[str] = None

class ReversibleLedger:
    """
    [C5-REAL] Ledger de Computación Reversible (Append-Only).
    Ningún byte de conocimiento se elimina (Zero Erasure).
    Las depreciaciones se procesan como 'Inversiones Epistémicas'.
    """
    def __init__(self):
        self._deltas: List[EpistemicDelta] = []
        
    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def assert_fact(self, content: str, parent_id: Optional[str] = None) -> str:
        """Inyecta conocimiento en el grafo (Operación Aditiva)."""
        fact_id = self._hash_content(content + str(time.time()))
        delta = EpistemicDelta(fact_id, "ASSERT", content, time.time(), parent_id)
        self._deltas.append(delta)
        return fact_id

    def deprecate_fact(self, fact_id: str) -> str:
        """
        [INVERSIÓN EPISTÉMICA] En lugar de `DELETE`, inyectamos un Delta Inverso.
        Preserva la exergía histórica y el linaje causal de auditoría.
        """
        # Verificación estructural: Asegurar que el hecho existe antes de invertirlo
        target = next((d for d in self._deltas if d.fact_id == fact_id and d.action == "ASSERT"), None)
        if not target:
            raise ValueError(f"Fact {fact_id} no encontrado en el ledger causal.")
            
        inversion_id = self._hash_content(f"INVERT_{fact_id}" + str(time.time()))
        delta = EpistemicDelta(inversion_id, "INVERT", target.content, time.time(), fact_id)
        self._deltas.append(delta)
        return inversion_id

    def resolve_current_state(self) -> Dict[str, str]:
        """
        Colapsa el DAG de Deltas en un estado de verdad (Proyección Biyectiva).
        Si existe un ASSERT y un INVERT del mismo linaje causal, se aniquilan lógicamente
        pero sobreviven termodinámicamente en `_deltas`.
        """
        state = {}
        inversions = set()
        
        # Pasada 1: Identificar inversiones
        for delta in self._deltas:
            if delta.action == "INVERT":
                inversions.add(delta.causal_parent)
                
        # Pasada 2: Resolver aserciones válidas
        for delta in self._deltas:
            if delta.action == "ASSERT" and delta.fact_id not in inversions:
                state[delta.fact_id] = delta.content
                
        return state

    def get_full_lineage(self) -> List[EpistemicDelta]:
        """Devuelve la cinta termodinámica completa sin pérdida de información."""
        return self._deltas
