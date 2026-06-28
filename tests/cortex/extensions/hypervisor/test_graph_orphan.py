import pytest
from dataclasses import replace
import logging

from cortex.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    BeliefVerdict,
    VerdictAction,
)
from cortex.extensions.hypervisor.belief_engine import BeliefEngine

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
        
    async def recall(self, project, limit=None, tenant_id="default", fact_type=None, offset=0):
        # Return all belief facts for project
        res = [f for f in self.facts if f.fact_type == "belief" and f.project == project]
        if limit:
            return res[:limit]
        return res


@pytest.mark.asyncio
async def test_cascading_quarantine_graph_orphan():
    """
    Test that quarantining a root belief automatically orphans and quarantines
    all dependent child beliefs recursively (O(1) topological sweep).
    """
    mock_db = MockEngine()
    engine = BeliefEngine(cortex_engine=mock_db)
    # Patch max_context for the stress test so it loads everything
    engine._max_context = 1000
    
    PROJECT = "test_graph"
    TENANT = "default"
    
    # 1. Generate an Axiomatic Root Belief
    root_belief = BeliefObject(
        content="Axioma: La gravedad es atractiva.",
        project=PROJECT,
        tenant_id=TENANT,
        confidence=BeliefConfidence.C5_AXIOMATIC,
        status=BeliefStatus.ACTIVE,
    )
    await engine._persist_belief(root_belief)
    
    # 2. Generate dependent children
    total_beliefs = 1
    children_l1 = []
    
    # 5 Children
    for i in range(5):
        child = BeliefObject(
            content=f"Consecuencia L1 {i}",
            project=PROJECT,
            tenant_id=TENANT,
            confidence=BeliefConfidence.C3_PROBABLE,
            status=BeliefStatus.ACTIVE,
            supported_by=(root_belief.id,)
        )
        await engine._persist_belief(child)
        children_l1.append(child)
        total_beliefs += 1
        
    # 10 Grandchildren per Child (50 total)
    for l1_child in children_l1:
        for j in range(10):
            child = BeliefObject(
                content=f"Consecuencia L2 {j}",
                project=PROJECT,
                tenant_id=TENANT,
                confidence=BeliefConfidence.C2_TENTATIVE,
                status=BeliefStatus.ACTIVE,
                supported_by=(l1_child.id,)
            )
            await engine._persist_belief(child)
            total_beliefs += 1

    # Assert all are active initially
    active_count = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "active")
    assert active_count == total_beliefs, f"Expected {total_beliefs} active beliefs, got {active_count}"

    # 3. Simulate QUARANTINE from CognitiveHandoff on Root
    verdict = BeliefVerdict(
        action=VerdictAction.QUARANTINE,
        model="claude-opus-4.6-premium",
        reason="Falsa premisa detectada. Aislamiento requerido.",
    )
    
    await engine._quarantine_belief(root_belief, verdict)
    
    # 4. Verify the state of the graph (Cascading Quarantine)
    active_count_post = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "active")
    quarantined_count = sum(1 for f in mock_db.facts if f.meta["belief_object"]["status"] == "quarantined")
    
    assert active_count_post == 0, f"Expected 0 active beliefs post-collapse, got {active_count_post}"
    assert quarantined_count == total_beliefs, f"Expected {total_beliefs} quarantined beliefs, got {quarantined_count}"
