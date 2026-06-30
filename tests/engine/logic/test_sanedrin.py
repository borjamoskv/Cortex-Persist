import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock

from babylon60.engine.logic.sanedrin import SanedrinCouncil, SanedrinNode
from babylon60.swarm.trust_registry import global_trust_registry


@pytest.fixture
def mock_router():
    router = AsyncMock()
    return router


@pytest.mark.asyncio
async def test_sanedrin_geometric_slashing(mock_router):
    """
    Test that the BFT Tribunal correctly slashes nodes that
    hallucinate or provide low Proof-of-Logic density.
    """
    # 1. Initialize the Council
    council = SanedrinCouncil(node_count=3, router=mock_router)

    # 2. Setup mock responses for execute_resilient
    # We simulate a scenario where N1 and N3 agree on A with high density,
    # but N2 hallucinates and picks B with low density.

    async def mock_execute_resilient(prompt):
        # Determine which node is calling based on system instruction
        system_instruction = prompt.system_instruction
        if "N1-Synthesizer" in system_instruction:
            out = '{"claim": "A", "proof_density": 0.95, "reasoning": "High confidence proof."}'
        elif "N3-Vector" in system_instruction:
            out = '{"claim": "A", "proof_density": 0.92, "reasoning": "Converging proof."}'
        else:  # N2-Logician
            out = '{"claim": "B", "proof_density": 0.40, "reasoning": "Hallucinated proof."}'

        # Wrap it in a mock result wrapper
        class MockRes:
            def is_err(self):
                return False

            def unwrap(self):
                return out

        return MockRes()

    mock_router.execute_resilient.side_effect = mock_execute_resilient

    fact_a = {"id": "A", "content": "Correct logic"}
    fact_b = {"id": "B", "content": "Flawed logic"}

    # Track the slashing
    with patch.object(global_trust_registry, "epistemic_slash") as mock_slash:
        with patch("cortex.engine.logic.sanedrin.apex_dispatcher.execute") as mock_dispatch:
            res = await council.convene(fact_a, fact_b)

            # Verify the consensus chose the right claim
            assert res["winning_node"] == "N1-Synthesizer"
            assert res["proof_density"] == 0.95

            # Verify N2 was slashed
            mock_slash.assert_called_once_with(
                "N2-Logician", "Failed Proof-of-Logic audit: Voted against BFT Quorum in Sanhedrin"
            )

            # Verify git sentinel was called
            mock_dispatch.assert_called_once()
            args, kwargs = mock_dispatch.call_args
            assert args[0] == "OP_GIT_SENTINEL"
            assert kwargs["force"] is False
