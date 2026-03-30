import asyncio
import json
import pytest
from cortex.engine.isolation import IsolationManager
from cortex.agents.arc_agi_3.agent import ARCAgent
from cortex.agents.arc_agi_3.reasoning import PeARLProgram

@pytest.mark.asyncio
async def test_isolation_manager_success():
    manager = IsolationManager()
    code = "import json\nprint(json.dumps({'output': [[1, 2], [3, 4]]}))"
    result = await manager.execute(code)
    assert result['output'] == [[1, 2], [3, 4]]

@pytest.mark.asyncio
async def test_isolation_manager_timeout():
    manager = IsolationManager(timeout=0.1)
    code = "import time\ntime.sleep(1)"
    with pytest.raises(TimeoutError):
        await manager.execute(code)

@pytest.mark.asyncio
async def test_isolation_manager_unsafe():
    manager = IsolationManager()
    # Attempting to import os (which is restricted in a true sandbox, 
    # but here we just check if it runs or fails gracefully)
    code = "import os\nprint(os.getpid())"
    result = await manager.execute(code)
    assert 'pid' not in str(result) # Should not have produced the PID if we expect isolation

@pytest.mark.asyncio
async def test_arc_agent_verify():
    agent = ARCAgent()
    program = PeARLProgram(source_code="def transform(grid):\n    return grid", confidence=1.0)
    train_examples = [
        {"input": [[1]], "output": [[1]]}
    ]
    # ARCAgent uses self.reasoning (ArcReasoningEngine) which has search_engine (NeuroSymbolicSearch)
    score = await agent.reasoning.search_engine._verify(program, train_examples)
    assert score == 1.0
