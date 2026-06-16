import pytest
import hashlib
from cortex.agents.ouroboros import LegionOrchestrator
from cortex.runtime.vesicular import VesicularRuntime

@pytest.mark.asyncio
async def test_ouroboros_legion_orchestrator():
    orchestrator = LegionOrchestrator(session_id="test_session")
    proposal = await orchestrator.spawn_ephemeral_agent(
        task_prompt="Calculate the meaning of life", 
        context_hash="abc123hash"
    )
    
    assert "cortex_taint" in proposal
    assert "content" in proposal
    assert "agent_id" in proposal
    assert proposal["agent_id"].startswith("jit_")
    
    # Verify taint locally
    from cortex.guards.sovereign_seals import verify_vesicular_taint
    assert verify_vesicular_taint(proposal, expected_agent_id=proposal["agent_id"])

@pytest.mark.asyncio
async def test_vesicular_runtime_death_protocol():
    runtime = VesicularRuntime(agent_id="test_death_protocol")
    proposal = await runtime.execute_and_die("Test Payload")
    
    assert "Vesicular Execution Output: Test Payload" in proposal["content"]
    assert "cortex_taint" in proposal
    assert proposal["agent_id"] == "test_death_protocol"
