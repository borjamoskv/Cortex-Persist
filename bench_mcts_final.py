
import asyncio
import logging
from typing import Any
from collections.abc import Mapping

# Mock signals for testing
def log_limbic(msg, source="", vibe=""):
    print(f"LIMBIC [{source}]: {msg}")

def log_motor(msg, action="", vibe=""):
    print(f"MOTOR [{action}]: {msg}")

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.engine.mcts import TestTimeComputeActuator
from cortex.engine.legion import SiegeResult

class MockLegion:
    async def forge(self, intent: str, context: dict[str, Any]) -> SiegeResult:
        mcts_iter = context.get("mcts_iteration", 0)
        # Simulate convergence to 0.88 exergy
        exergy_val = min(0.88, 0.5 + 0.05 * mcts_iter)
        await asyncio.sleep(0.01)
        return SiegeResult(
            success=False, 
            final_code=f"code_{mcts_iter}", 
            exergy=exergy_val,
            vulnerabilities=[],
            cycles=mcts_iter + 1
        )

async def main():
    legion = MockLegion()
    # iterations=40, batch_size=5 -> Should exit around batch 5 or 6 (iter 25-30)
    actuator = TestTimeComputeActuator(legion=legion, iterations=40, batch_size=5)
    
    import time
    start = time.time()
    result = await actuator.active_inference("test_intent", {"initial": "state"})
    end = time.time()
    
    print(f"Time: {end - start:.2f}s")
    print(f"Result max exergy: {result.exergy}")
    print(f"Iterations completed: {result.cycles}")

if __name__ == "__main__":
    asyncio.run(main())
