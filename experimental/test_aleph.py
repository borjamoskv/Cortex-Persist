import asyncio
import os
import time

from cortex.swarm.centauro_engine import CentauroEngine, Formation
from cortex.swarm.byzantine import ByzantineConsensus

def mock_execute(self, proposals: dict[str, str]) -> str | None:
    # Force a deadlock outcome every time
    return None

# Override to force a failure (it's a sync function in ByzantineConsensus)
ByzantineConsensus.execute_consensus = mock_execute

async def test_aleph_omega():
    os.environ["CORTEX_NO_LLM"] = "1"
    print("Initializing CentauroEngine with ALEPH-Ω integration...")
    engine = CentauroEngine()
    
    print("\n--- Mission: Test Axiomatic Leap ---")
    
    t0 = time.time()
    # Trigger a mission. Standard consensus will fail, so it should leap.
    result = await engine.engage("Resolve the Riemann Hypothesis", formation=Formation.BLITZ)
    t1 = time.time()
    
    print("\n[RESULT]")
    print(f"Status: {result.get('status')}")
    print(f"Formation: {result.get('formation')}")
    if "reason" in result:
        print(f"Reason: {result.get('reason')}")
    print(f"Solution: {result.get('solution')}")
    print(f"Time taken: {t1-t0:.2f}s")
    
if __name__ == "__main__":
    asyncio.run(test_aleph_omega())
