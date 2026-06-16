import pytest
from cortex.agents.world_model_agent import WorldModelWebAgent
from cortex.guards.zk_guard import ZKSwarmGuard, VoidStateSecurityError

@pytest.mark.asyncio
async def test_world_model_agent_zk_swarm_guard():
    """
    AX-044: Verify that the WorldModelWebAgent correctly signs its structural
    decisions, and that the ZKSwarmGuard mathematically validates them without aborting.
    """
    # 1. Initialize agent (automatically generates Ed25519 identity)
    agent = WorldModelWebAgent(session_id="test_session")
    
    # 2. Agent executes inference and mathematically signs the proposal
    proposal = agent.execute_react_step("<html>DOM observation...</html>")
    
    # 3. ZK Guard intercept boundary
    guard = ZKSwarmGuard(enforce_on_types=("decision",))
    
    try:
        # The guard should mathematically PASS
        await guard.verify_integrity(
            content=proposal["content"],
            fact_type=proposal["fact_type"],
            meta=proposal["meta"]
        )
    except VoidStateSecurityError as e:
        pytest.fail(f"ZK-SWARM Proof Failed: {e}")
        
    assert True
