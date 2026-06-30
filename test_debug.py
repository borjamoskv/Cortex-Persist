import asyncio
from unittest.mock import AsyncMock, patch

from cortex_extensions.red_team.hydra_chaos import ChaosScenario, HydraChaosEngine, MockRedisClient
from cortex_extensions.swarm.error_ghost_pipeline import ErrorGhostPipeline


async def main():
    ErrorGhostPipeline._instance = None
    engine = HydraChaosEngine()
    mock = MockRedisClient()
    
    with patch(
        "cortex_extensions.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
        new_callable=AsyncMock,
        return_value=1,
    ):
        res = await engine.execute_scenario(ChaosScenario.KILL, mock)
    print(f"Result: {res}")
    print(f"Stats: {ErrorGhostPipeline().stats}")

asyncio.run(main())
