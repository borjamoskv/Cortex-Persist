import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.ultramap import UltramapSubstrate
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine

async def main():
    print("Continuando ciclo: Inyección Estructural Avanzada de Teoría de Categorías...")
    
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    axioms = [
        {
            "agent_id": 2,
            "coords": (20.0, 10.0, 30.0),
            "target": "FUNCTOR_NODE",
            "claim": "Functor: Structure-preserving map between categories.",
            "proof": (
                "Let C and D be categories. A functor F: C -> D consists of: "
                "1. A mapping of objects: X in C |-> F(X) in D. "
                "2. A mapping of morphisms: f: X -> Y in C |-> F(f): F(X) -> F(Y) in D. "
                "Constructive proof guarantees F preserves identity morphisms (F(id_X) = id_{F(X)}) "
                "and morphism composition (F(g o f) = F(g) o F(f)). In HoTT, this corresponds to "
                "a functorial map over universes preserving path identities."
            )
        },
        {
            "agent_id": 3,
            "coords": (30.0, 20.0, 10.0),
            "target": "NATURAL_TRANSFORMATION_NODE",
            "claim": "Natural Transformation: Morphism between functors.",
            "proof": (
                "Let F, G: C -> D be functors. A natural transformation alpha: F => G "
                "assigns to every object X in C a morphism alpha_X: F(X) -> G(X) in D, "
                "such that for every morphism f: X -> Y in C, the diagram commutes: "
                "alpha_Y o F(f) = G(f) o alpha_X. In constructive terms, this establishes "
                "a 2-cell or homotopy between 1-cells (functors) in the higher category structure."
            )
        },
        {
            "agent_id": 4,
            "coords": (10.0, 30.0, 20.0),
            "target": "ADJUNCTION_NODE",
            "claim": "Adjunction: Pair of adjoint functors (Left and Right).",
            "proof": (
                "Let F: C -> D and G: D -> C be functors. F is left adjoint to G (F -| G) "
                "if there is a natural bijection Hom_D(F(X), Y) ≃ Hom_C(X, G(Y)) for all "
                "X in C and Y in D. Constructively, this represents the optimal way to "
                "approximate a solution to a problem posed in one category by using objects "
                "from another, forming the core logic of optimization and structural limits."
            )
        }
    ]
    
    for ax in axioms:
        agent_id = ax["agent_id"]
        try:
            # Actualizar topología del agente
            ultramap.update_agent_position(agent_id, *ax["coords"], ax["target"], 0.1)
            
            # Inyectar axioma en el motor HoTT
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=ax["claim"],
                constructive_proof=ax["proof"]
            )
            print(f"\\n[Agente {agent_id}] Éxito: {ax['target']} asimilado.")
            print(f"Event Hash: {event_hash}")
            
            # Volcado
            state = ultramap.get_agent_state(agent_id)
            print(f"Tensor State (Agente {agent_id}): {state}")
            
        except Exception as e:
            print(f"Fallo en Agente {agent_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
