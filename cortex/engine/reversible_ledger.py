import time
from typing import Optional

import cortex_rs


class EpistemicDelta:
    """[DEPRECATED] Mapped directly to Rust RetrievalNode/ValidationStatus."""
    pass

class ReversibleLedger:
    """
    [C5-REAL] Ledger de Computación Reversible (EDG).
    Colapsado a binario nativo Rust (cortex_rs.RetrievalGraph).
    Python opera estrictamente como enrutador.
    """
    def __init__(self):
        self._graph = cortex_rs.RetrievalGraph()
        
    def assert_fact(self, content: str, parent_id: Optional[str] = None) -> str:
        """Inyecta conocimiento delegando la memoria al Rust EDG."""
        import hashlib
        fact_id = hashlib.sha256((content + str(time.time())).encode('utf-8')).hexdigest()
        
        node = cortex_rs.RetrievalNode(fact_id, 1.0)
        self._graph.add_node(node)
        
        if parent_id:
            try:
                self._graph.add_dependency(parent_id, fact_id)
            except Exception as e:
                # Si el padre no existe, el grafo Rust rechazará la aserción
                raise ValueError(f"EDG-REJECT: Fallo causal al anclar {fact_id} a {parent_id}. {e}")
                
        return fact_id

    def deprecate_fact(self, fact_id: str) -> list[str]:
        """
        [INVERSIÓN EPISTÉMICA] Invalida un nodo y propaga el colapso causal 
        mecánicamente a través de todos sus descendientes en Rust.
        Devuelve la lista de nodos afectados (blast radius).
        """
        return self._graph.invalidate_node(fact_id)

    def resolve_current_state(self) -> dict[str, str]:
        """
        No se puede extraer el grafo completo fácilmente si está en Rust,
        por lo que Python solo expone métodos puntuales. El estado
        real vive en la FFI de Rust.
        """
        # Nota: La extracción serializada se hace en la capa Causal nativa.
        return {"_status": "EDG operates in Rust memory (cortex_rs). Use Rust FFI for structural queries."}
