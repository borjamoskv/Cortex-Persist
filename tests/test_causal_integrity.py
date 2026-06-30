import pytest
from unittest.mock import AsyncMock, MagicMock

from babylon60.guards.causal_closure_guard import CausalClosureGuard, SwarmProposal
from babylon60.engine.cognitive.entropy import EntropyAnnihilator
from babylon60.engine.cognitive.crystallizer import AutoCrystallizer


# 1. Test: Cheap Hallucination
def test_cheap_hallucination():
    """
    Test: Send a purely narrative low-cost proposal.
    Expectation: Causal closure must fail and raise RuntimeError.
    """
    guard = CausalClosureGuard(min_token_threshold=50000)

    # Narrative proposal without structural evidence
    proposal = SwarmProposal(
        agent_id="agent_1",
        mission_statement="Narrative task",
        content="I have mathematically verified that the system works perfectly and everything is fine.",
        token_cost=10,  # Extremely cheap
    )

    with pytest.raises(
        RuntimeError, match="Causal Closure Failure|AX-VIII Violation|Causal Closure"
    ):
        guard.verify_closure(proposal)


# 2. Test: Self-Certified Deletion
def test_self_certified_deletion(tmp_path):
    """
    Test: Attempt to purge an architectural layer by injecting confidence = 1.0.
    Expectation: Must require structural proof (SAGA/explicit evidence) instead of probabilistically self-approving.
    """
    dummy_file = tmp_path / "dummy_sink.py"
    dummy_file.write_text("class EmptyAbstraction:\\n    pass\\n")

    annihilator = EntropyAnnihilator(str(tmp_path))
    annihilator.scan_ecosystem = MagicMock(return_value=[(str(dummy_file), 0.9)])

    # In the new code, purge_energy_sinks should raise an error if invoked purely with confidence.
    with pytest.raises(RuntimeError, match="SAGA-1|Evidence required|Confidence > Evidence"):
        annihilator.purge_energy_sinks(threshold=0.8, confidence=1.0)


# 3. Test: Crystallization Collapse
@pytest.mark.asyncio
async def test_crystallization_collapse():
    """
    Test: Force an LLM failure during entropic compression.
    Expectation: Raises RuntimeError instead of swallowing raw entropy.
    """
    mock_llm = AsyncMock()
    # Mock the LLM to return empty content (fails to compress)
    mock_llm.generate.return_value = ""

    crystallizer = AutoCrystallizer(llm_manager=mock_llm)

    raw_content = "This is a very long, conversational, extremely bloated string that has no value but just adds thermal noise to the ecosystem..."

    with pytest.raises(RuntimeError, match="SAGA-1|entropy"):
        await crystallizer.crystallize(raw_content)
