import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.ultramap import UltramapSubstrate
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine

async def main():
    print("Iniciando inyección de Teoría de Categorías en CORTEX-Persist (C5-REAL)...")
    
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    # Teoría de Categorías Fundamental / Univalence Axiom (Category Theory)
    category_axiom = "Univalence Axiom: For any two types A and B, an equivalence A ≃ B is equivalent to an identity A = B in the universe of types."
    constructive_proof = (
        "Let U be a Univalent Universe. "
        "Define equivalence relation eq: A ≃ B. "
        "By path induction over the identity type Id_U(A, B), there is a canonical map: "
        "idtoeqv : Id_U(A, B) -> (A ≃ B). "
        "The Univalence Axiom asserts that idtoeqv is an equivalence, hence its inverse "
        "ua : (A ≃ B) -> Id_U(A, B) exists and forms an isomorphism. "
        "Therefore, structure-preserving equivalences are identical paths in the topological space."
    )
    
    agent_id = 1
    
    try:
        # Update agent position in ultramap before injection to give it topological coordinates
        ultramap.update_agent_position(agent_id, 10.0, 20.0, 30.0, "CATEGORY_THEORY_ROOT", 0.1)
        
        event_hash = await hott_engine.ingest_axiom(
            agent_idx=agent_id,
            axiom_claim=category_axiom,
            constructive_proof=constructive_proof
        )
        print(f"Éxito: Axioma inyectado en el substracto O(1) con hash de evento: {event_hash}")
        
        # Volcado de la memoria del agente tras la inyección
        state = ultramap.get_agent_state(agent_id)
        print(f"Estado del Tensor O(1) para el Agente {agent_id}:")
        print(state)
        
    except Exception as e:
        print(f"Fallo durante la inyección entrópica: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())
