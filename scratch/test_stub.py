import asyncio
import logging
import sys

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

from cortex.pipeline import PipelineRequest, PipelineStatus
from cortex.pipeline.orchestrator import CortexOrchestrator
from cortex.pipeline.executor import AgentExecutor


async def run_test():
    print("--- Starting Run Test ---")
    executor = AgentExecutor()
    executor._provider = None
    executor._router = None

    async def _mock_ensure_none():
        print("DEBUG: _mock_ensure_none called")
        return None

    executor._ensure_provider = _mock_ensure_none
    executor._ensure_router = _mock_ensure_none

    orch = CortexOrchestrator(agent_executor=executor)
    req = PipelineRequest(intent="test with executor")

    print("DEBUG: Calling orch.run(req)")
    result = orch.run(req)
    print("DEBUG: orch.run(req) returned")
    print(f"DEBUG: result status: {result.status}")
    print(f"DEBUG: result output: {result.output}")


if __name__ == "__main__":
    asyncio.run(run_test())
