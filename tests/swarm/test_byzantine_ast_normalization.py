# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import pytest
from babylon60.extensions.swarm.byzantine import ByzantineConsensus


@pytest.mark.asyncio
async def test_byzantine_ast_normalization():
    """
    Validates that minor differences in comments, whitespaces, and formatting
    are normalized by the AST parser, ensuring semantic consensus is achieved.
    """
    consensus = ByzantineConsensus(tolerance_threshold=0.5)
    consensus.register_node("agent_1")
    consensus.register_node("agent_2")

    # Proposals have identical AST logic but different comments and spacing
    proposal_1 = "x = 100\n# this is a comment"
    proposal_2 = "x   =   100  "

    # Verify that the normalized representation is identical
    norm_1 = consensus._normalize_proposal(proposal_1)
    norm_2 = consensus._normalize_proposal(proposal_2)
    assert norm_1 == norm_2
    assert "# this is a comment" not in norm_1

    # Verify that they produce the exact same hash
    hash_1 = consensus._hash_proposal(proposal_1)
    hash_2 = consensus._hash_proposal(proposal_2)
    assert hash_1 == hash_2

    # Execute consensus
    proposals = {
        "agent_1": proposal_1,
        "agent_2": proposal_2,
    }
    winner = await consensus.execute_consensus(proposals)
    assert winner is not None
    # Winner can be any of the raw inputs because they resolve to the same AST hash
    assert winner in (proposal_1, proposal_2)


@pytest.mark.asyncio
async def test_byzantine_ast_normalization_different_logic():
    """
    Validates that actual logic differences (different ASTs) do not match
    and consensus fails if they do not meet the threshold.
    """
    consensus = ByzantineConsensus(tolerance_threshold=0.6)
    consensus.register_node("agent_1")
    consensus.register_node("agent_2")

    # Different code logic
    proposal_1 = "x = 1"
    proposal_2 = "x = 2"

    hash_1 = consensus._hash_proposal(proposal_1)
    hash_2 = consensus._hash_proposal(proposal_2)
    assert hash_1 != hash_2

    proposals = {
        "agent_1": proposal_1,
        "agent_2": proposal_2,
    }
    winner = await consensus.execute_consensus(proposals)
    # 50% match does not reach 60% threshold, so consensus must fail
    assert winner is None
