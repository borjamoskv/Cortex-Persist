import asyncio
import pytest
from cortex.engine.jit import JITConceptEngine

@pytest.mark.asyncio
async def test_jit_v2_mcts_stress():
    engine = JITConceptEngine(tenant_id="test_tenant_stress")
    observation = {"id": "arc_pattern_001", "type": "grid_transform"}
    
    # Run 10 parallel inductions to test concurrency and state isolation
    tasks = [engine.induce_program_mcts(observation, iterations=200) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    for r in results:
        assert r["status"] == "CRYSTALLIZED"
        assert r["confidence"] > 0.99
        assert "concept_jit_mcts_" in r["program_id"]
    
    print("\n[JIT-STRESS] All 10 parallel inductions converged with high confidence.")

if __name__ == "__main__":
    asyncio.run(test_jit_v2_mcts_stress())
