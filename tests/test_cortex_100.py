import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from cortex.swarm.orchestrator import MasterOrchestrator
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager
from cortex.swarm.bus import AsyncSignalBus
from cortex.swarm.partitioner import SwarmEnclave

@pytest.mark.asyncio
async def test_swarm_100_crystallization():
    # Setup
    bus = AsyncSignalBus()
    factory = MagicMock(spec=SwarmFactory)
    manager = SwarmManager(bus=bus)
    
    # Mock recruitment of 100 agents
    factory.recruit_full_swarm = AsyncMock(return_value={
        "P0": [f"p0-{i}" for i in range(30)],
        "P1": [f"p1-{i}" for i in range(40)],
        "P2": [f"p2-{i}" for i in range(30)],
    })
    
    # Mock manager dispatch/shard
    manager.dispatch = AsyncMock(return_value={
        "status": "success",
        "content": "Work done",
        "metadata": {"exergy_yield": 0.5}
    })
    
    orchestrator = MasterOrchestrator()
    orchestrator.factory = factory
    orchestrator.enclaves[SwarmEnclave.EXECUTION] = manager
    
    # Execute Swarm-100
    goal = "Synthesize a global exergy extraction strategy for all connected nodes."
    result = await orchestrator.execute_swarm_100(goal)
    
    # Assertions
    assert result["agents_deployed"] == 100
    assert result["success_rate"] == "100.0%"
    assert result["total_exergy_extracted"] == 50.0  # 100 * 0.5
    assert result["status"] == "crystallized"
    
    print("\nVerified: CORTEX-100 (100 Agents) Crystallization Logic OK.")

if __name__ == "__main__":
    asyncio.run(test_swarm_100_crystallization())
