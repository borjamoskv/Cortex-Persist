import hashlib
import time
from dataclasses import dataclass
from typing import Optional

import cortex_rs


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
    [C5-REAL] Ledger de Computación Reversible (EDG).
    Colapsado a binario nativo Rust (cortex_rs.RetrievalGraph).
    Python opera como enrutador y mantiene el linaje local.
    """
    def __init__(self):
        self._graph = cortex_rs.RetrievalGraph()
        self._deltas: list[EpistemicDelta] = []
        
    def assert_fact(self, content: str, parent_id: Optional[str] = None) -> str:
        """Inyecta conocimiento delegando la memoria al Rust EDG y agregando el delta."""
        fact_id = hashlib.sha256((content + str(time.time())).encode('utf-8')).hexdigest()
        
        node = cortex_rs.RetrievalNode(fact_id, 1.0)
        self._graph.add_node(node)
        
        if parent_id:
            try:
                self._graph.add_dependency(parent_id, fact_id)
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                # Si el padre no existe, el grafo Rust rechazará la aserción
                raise ValueError(f"EDG-REJECT: Fallo causal al anclar {fact_id} a {parent_id}. {e}")
                
        delta = EpistemicDelta(fact_id, "ASSERT", content, time.time(), parent_id)
        self._deltas.append(delta)
        return fact_id

    def deprecate_fact(self, fact_id: str) -> str:
        """
        [INVERSIÓN EPISTÉMICA] Invalida un nodo y propaga el colapso causal 
        mecánicamente a través de todos sus descendientes en Rust.
        """
        target = next((d for d in self._deltas if d.action == "ASSERT" and d.fact_id == fact_id), None)
        if not target:
            raise ValueError(f"Fact {fact_id} no encontrado en el ledger causal.")
            
        self._graph.invalidate_node(fact_id)
        
        inversion_id = hashlib.sha256(f"INVERT_{fact_id}_{time.time()}".encode()).hexdigest()
        delta = EpistemicDelta(inversion_id, "INVERT", target.content, time.time(), fact_id)
        self._deltas.append(delta)
        return inversion_id

    def resolve_current_state(self) -> dict[str, str]:
        """Colapsa el DAG de Deltas en un estado de verdad."""
        state = {}
        inversions = set()
        
        for delta in self._deltas:
            if delta.action == "INVERT":
                inversions.add(delta.causal_parent)
                
        for delta in self._deltas:
            if delta.action == "ASSERT" and delta.fact_id not in inversions:
                state[delta.fact_id] = delta.content
                
        return state

    def get_full_lineage(self) -> list[EpistemicDelta]:
        """Devuelve la cinta termodinámica completa sin pérdida de información."""
        return self._deltas
