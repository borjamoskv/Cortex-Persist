import pytest
import asyncio
from cortex.engine.swarm_10k import BFTConsensusEngine

@pytest.mark.asyncio
async def test_bft_quorum_requires_three_assertions():
    engine = BFTConsensusEngine(required_quorum=3)
    
    topic_id = "test_topic"
    fact_hash = "abc123hash"
    
    # 1st agent proposes
    quorum_reached = await engine.propose_fact(fact_hash, "agent_1", topic_id)
    assert quorum_reached is False
    
    # 2nd agent proposes
    quorum_reached = await engine.propose_fact(fact_hash, "agent_2", topic_id)
    assert quorum_reached is False
    
    # 3rd agent proposes (Quorum reached)
    quorum_reached = await engine.propose_fact(fact_hash, "agent_3", topic_id)
    assert quorum_reached is True
    
    # 4th agent proposes (Quorum still reached)
    quorum_reached = await engine.propose_fact(fact_hash, "agent_4", topic_id)
    assert quorum_reached is True

@pytest.mark.asyncio
async def test_bft_quorum_with_conflicting_proposals():
    engine = BFTConsensusEngine(required_quorum=3)
    
    topic_id = "test_topic"
    hash_a = "hash_A"
    hash_b = "hash_B"
    
    # Agents 1 and 2 propose hash_A
    assert await engine.propose_fact(hash_a, "agent_1", topic_id) is False
    assert await engine.propose_fact(hash_a, "agent_2", topic_id) is False
    
    # Agent 3 proposes hash_B (Conflict)
    assert await engine.propose_fact(hash_b, "agent_3", topic_id) is False
    
    # Agent 4 proposes hash_B
    assert await engine.propose_fact(hash_b, "agent_4", topic_id) is False
    
    # Agent 5 proposes hash_A (Quorum for A reached!)
    assert await engine.propose_fact(hash_a, "agent_5", topic_id) is True
