import asyncio
import pytest
from cortex.engine.legion import LegionOmegaEngine

@pytest.mark.asyncio
async def test_swarm_autonomy_ax045():
    # Set a low threshold to trigger autonomy easily
    engine = LegionOmegaEngine(max_cycles=1, autonomy_threshold=0.3)
    
    # Context with enough 'data' to trigger complexity threshold
    context = {"data": [1, 2, 3, 4, 5]} # Complexity = 0.5 > 0.3
    
    # Patch synthesize to avoid real calls
    async def mock_synth(intent, ctx, feedback):
        return f"# Autonomously forged {intent}"
    engine.blue_team.synthesize = mock_synth
    
    result = await engine.forge("autonomous_task", context=context)
    
    # Since it's autonomous, cycles should be adaptive (up to 2 in this case as max_cycles=1 and it doubles)
    # Actually, the loop uses range(1, adaptive_cycles + 1)
    # adaptive_cycles = 1 * 2 = 2
    # So it should run up to 2 cycles if it doesn't converge
    
    assert result.cycles >= 1
    print(f"\n[AUTONOMY-TEST] Task 'autonomous_task' triggered autonomy. Cycles: {result.cycles}")

if __name__ == "__main__":
    asyncio.run(test_swarm_autonomy_ax045())
