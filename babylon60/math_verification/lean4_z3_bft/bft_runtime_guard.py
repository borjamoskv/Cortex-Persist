"""
CORTEX-PERSIST C5-REAL RUNTIME GUARD
Extracción Estructural de Fase 4 (Lean 4 -> Python Runtime)
"""

def bft_safety_guard(node_id: int, height: int, vote_count: int, is_honest: bool) -> None:
    """
    Cristalización Runtime del Isomorfismo SMT (HonestRule).
    
    Axioma Lean 4 Demostrado:
    theorem bft_safety_invariant: isHonest = true -> voteCount <= 1
    
    Cualquier estado que rompa este isomorfismo provocará un Causal Crash.
    """
    if is_honest and vote_count > 1:
        # FAIL-FAST TERMODINÁMICO (L12.K1)
        # La prevención de fallos es Anergía. Se fuerza el cierre del proceso.
        raise RuntimeError(
            f"[FATAL C5-REAL] Fractura Termodinámica (Byzantine Fault). "
            f"Nodo {node_id} se declara honesto pero emitió {vote_count} votos en altura {height}. "
            "Apoptosis Causal iniciada."
        )
