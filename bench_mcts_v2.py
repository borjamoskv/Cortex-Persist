import asyncio
import time
from cortex.engine.mcts import MCTS_ACTUATOR
from cortex.engine.legion import SiegeResult

class MockLegion:
    async def forge(self, intent, context):
        await asyncio.sleep(0.05)
        mcts_iter = context.get("mcts_iteration", 0)
        # Simulate increasing exergy up to 0.88 to trigger plateau exit
        exergy_val = min(0.88, 0.5 + 0.05 * mcts_iter)
        return SiegeResult(success=True, final_code="def logic(): pass", cycles=1, vulnerabilities=[], exergy=exergy_val, entropy_delta=0.0)

async def main():
    actuator = MCTS_ACTUATOR
    actuator.legion = MockLegion()
    actuator.iterations = 20
    actuator.batch_size = 5
    
    start = time.time()
    res = await actuator.active_inference("Test PUCT + Early Exit", {"test": True})
    elapsed = time.time() - start
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Result cycles (from iteration): {res.cycles}")
    print(f"Result max exergy: {res.exergy}")

if __name__ == "__main__":
    asyncio.run(main())
