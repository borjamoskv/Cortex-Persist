import pytest
import asyncio
import time
from cortex.engine.swarm_10k import BFTConsensusEngine

@pytest.mark.asyncio
async def test_swarm_10k_stress_bft():
    engine = BFTConsensusEngine(required_quorum=3)
    
    # Simulate 10,000 agents proposing the same fact to measure contention
    num_agents = 10000
    topic_id = "global_stress_test"
    fact_hash = "0xSTRESS_TEST_HASH_A"
    
    start_time = time.perf_counter()
    
    async def agent_propose(agent_index: int):
        agent_id = f"agent_{agent_index}"
        # Everyone proposes the exact same fact
        return await engine.propose_fact(fact_hash, agent_id, topic_id)
        
    # Launch all 10,000 propositions concurrently
    tasks = [agent_propose(i) for i in range(num_agents)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # After 10,000 proposals, the quorum must be reached (True)
    # The first 2 will be False, the rest will be True
    true_count = sum(1 for r in results if r)
    false_count = sum(1 for r in results if not r)
    
    assert false_count == 2
    assert true_count == num_agents - 2
    
    # Performance assertion: 10k asynchronous calls should complete relatively quickly in memory
    print(f"10,000 agents completed BFT Consensus in {duration:.3f} seconds")
    assert duration < 5.0, f"Stress test took too long: {duration:.3f}s"
