import asyncio
import logging

from cortex.extensions.hypervisor.belief_engine import BeliefEngine
from cortex.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    BeliefVerdict,
    VerdictAction,
)

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("cortex_poc")
logger.setLevel(logging.INFO)

class MockFact:
    def __init__(self, content, fact_type, project, meta, confidence):
        self.content = content
        self.fact_type = fact_type
        self.project = project
        self.meta = meta
        self.confidence = confidence

class MockEngine:
    def __init__(self):
        self.facts = []
        
    async def store(self, content, fact_type, project, source, meta, confidence):
        # If updating a quarantined belief, replace the existing one in facts
        obj_dict = meta.get("belief_object", {})
        belief_id = obj_dict.get("id")
        
        # Remove old version if it exists
        self.facts = [f for f in self.facts if f.meta.get("belief_object", {}).get("id") != belief_id]
        
        self.facts.append(MockFact(content, fact_type, project, meta, confidence))
        
    async def recall(self, query, project, limit):
        # We ignore complex query matching for this mock and just return all belief facts for project
        return [f for f in self.facts if f.fact_type == "belief" and f.project == project][:limit]

async def stress_test_max_exergy():
    print("==========================================================")
    print(" 💥 PRUEBA DE ESTRÉS DE MÁXIMA EXERGÍA (CORTEX NATIVE) 💥")
    print("==========================================================\n")
    
    mock_db = MockEngine()
    engine = BeliefEngine(cortex_engine=mock_db)
    # Patch max_context for the stress test so it loads everything
    engine._max_context = 1000
    
    PROJECT = "stress_test"
    TENANT = "default"
    
    # 1. Generate an Axiomatic Root Belief
    root_belief = BeliefObject(
        content="La termodinámica computacional es la única fuente de verdad (C5).",
        project=PROJECT,
        tenant_id=TENANT,
        confidence=BeliefConfidence.C5_AXIOMATIC,
        status=BeliefStatus.ACTIVE,
    )
    await engine._persist_belief(root_belief)
    
    # 2. Generate a massive fractal dependency tree
    # Level 1: 5 children depending on Root
    print(f"[*] Inyectando nodo raíz: {root_belief.id}")
    
    total_beliefs = 1
    
    children_l1 = []
    for i in range(5):
        child = BeliefObject(
            content=f"Deducción L1 #{i} basada en termodinámica.",
            project=PROJECT,
            tenant_id=TENANT,
            confidence=BeliefConfidence.C3_PROBABLE,
            status=BeliefStatus.ACTIVE,
            supported_by=(root_belief.id,)
        )
        await engine._persist_belief(child)
        children_l1.append(child)
        total_beliefs += 1
        
    # Level 2: 10 grandchildren for each L1 child (50 total)
    children_l2 = []
    for l1_child in children_l1:
        for j in range(10):
            child = BeliefObject(
                content=f"Deducción L2 #{j} basada en L1 {l1_child.id[:8]}.",
                project=PROJECT,
                tenant_id=TENANT,
                confidence=BeliefConfidence.C2_TENTATIVE,
                status=BeliefStatus.ACTIVE,
                supported_by=(l1_child.id,)
            )
            await engine._persist_belief(child)
            children_l2.append(child)
            total_beliefs += 1

    # Level 3: 5 great-grandchildren for each L2 child (250 total)
    for l2_child in children_l2:
        for k in range(5):
            child = BeliefObject(
                content=f"Deducción L3 #{k} basada en L2 {l2_child.id[:8]}.",
                project=PROJECT,
                tenant_id=TENANT,
                confidence=BeliefConfidence.C1_HYPOTHESIS,
                status=BeliefStatus.ACTIVE,
                supported_by=(l2_child.id,)
            )
            await engine._persist_belief(child)
            total_beliefs += 1

    print(f"[*] Topología fractal generada: {total_beliefs} creencias activas.")
    
    # Check DB
    active_count = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "active")
    print(f"[*] Creencias en Base de Datos: {len(mock_db.facts)} ({active_count} ACTIVAS)")

    print("\n[!] SIMULANDO COLAPSO DE CIMIENTO (BFT GUARD ACTIVADO)")
    print(f"[!] Auditor Premium Opus declara la raíz {root_belief.id} en cuarentena por contradicción grave.")
    
    # 3. Simulate QUARANTINE from CognitiveHandoff
    verdict = BeliefVerdict(
        action=VerdictAction.QUARANTINE,
        model="claude-opus-4.6-premium",
        reason="Falsa premisa detectada: La entropía es reversible según el modelo Q. Aislamiento requerido.",
    )
    
    import time
    t0 = time.time()
    await engine._quarantine_belief(root_belief, verdict)
    t1 = time.time()
    
    print("\n==========================================================")
    print(f" ⏳ TIEMPO DE ORFANDAD TOPOLÓGICA: {(t1-t0)*1000:.2f} ms")
    print("==========================================================")
    
    # 4. Verify the state of the graph
    active_count = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "active")
    quarantined_count = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "quarantined")
    
    print(f"[*] Creencias activas post-colapso:     {active_count}")
    print(f"[*] Creencias huérfanas (quarantined): {quarantined_count}")
    
    if active_count == 0 and quarantined_count == total_beliefs:
        print("\n✅ ESTRÉS SUPERADO: El vacío termodinámico es absoluto. No hay fugas de exergía.\n")
    else:
        print(f"\n❌ FALLO DE ORFANDAD: Quedan {active_count} activas de {total_beliefs}. Malla corrupta.\n")

if __name__ == "__main__":
    asyncio.run(stress_test_max_exergy())
