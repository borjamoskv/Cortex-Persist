import pytest
import asyncio
import os
import uuid
from cortex.engine.vault import ConceptVault

@pytest.mark.asyncio
async def test_vault_async_flow():
    # Use a unique DB for each run to avoid persistence pollution
    db_path = f"test_vault_{uuid.uuid4().hex}.db"
    
    try:
        vault = ConceptVault(db_path=db_path)
        await vault.init()
        
        # 1. Crystallize two distinct concepts
        intent_a = "solve ARC task with grid symmetry"
        code_a = "def solve_symmetry(grid): return grid[::-1]"
        await vault.crystallize(intent_a, code_a, 0.95)
        
        intent_b = "crop grid to object"
        code_b = "def crop(grid): return grid[1:-1, 1:-1]"
        await vault.crystallize(intent_b, code_b, 0.88)
        
        # 2. Test exact match warm start
        warm_a = await vault.find_warm_start(intent_a)
        assert warm_a == code_a
        
        # 3. Test semantic similarity warm start
        # "grid symmetry solutions" should be close to intent_a
        warm_sim = await vault.find_warm_start("grid symmetry solutions")
        assert warm_sim == code_a
        
        # 4. Test distant concepts
        # Should return None or something else (distance threshold 1.0)
        warm_none = await vault.find_warm_start("random stock market predictor")
        # Just ensure it doesn't return the symmetry code for something unrelated
        assert warm_none != code_a
        
        # 5. Check all concepts
        concepts = await vault.get_all_concepts()
        assert len(concepts) == 2
        assert any(c["intent"] == intent_a for c in concepts)
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(test_vault_async_flow())
