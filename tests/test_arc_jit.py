import pytest
import asyncio
from cortex.engine.jit import JITConceptEngine
from cortex.engine.heuristic import MockHeuristicEngine

@pytest.mark.asyncio
async def test_arc_jit_rotation():
    engine = JITConceptEngine(tenant_id="arc_test")
    
    # 2x2 grid rotated 90 deg
    example = {
        "input": [[1, 2], [3, 4]],
        "output": [[3, 1], [4, 2]]
    }
    
    # Induce program (iterations=500 for robust search)
    result = await engine.induce_program_mcts(example, iterations=500)
    
    assert result["status"] == "CRYSTALLIZED"
    assert "rotate_90" in result["ops"]
    print(f"\n[ARC-JIT] Synthesis successful: {result['ops']}")

@pytest.mark.asyncio
async def test_arc_jit_puct_convergence():
    heuristic = MockHeuristicEngine()
    engine = JITConceptEngine(tenant_id="arc_test_puct", heuristic_engine=heuristic)
    
    example = {
        "input": [[1, 2], [3, 4]],
        "output": [[3, 1], [4, 2]]
    }
    
    # Prove that the biased PUCT heuristic solves it in drastically fewer iterations
    result = await engine.induce_program_mcts(example, iterations=10)
    
    assert result["status"] == "CRYSTALLIZED", "Engine failed to crystallize concept."
    assert "rotate_90" in result["ops"], "Engine failed to select rotate_90."
    print(f"\n[ARC-JIT PUCT] Fast synthesis via Heuristic successful: {result['ops']}")

if __name__ == "__main__":
    asyncio.run(test_arc_jit_rotation())
    asyncio.run(test_arc_jit_puct_convergence())
