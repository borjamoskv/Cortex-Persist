import pytest
import os
import ast
from unittest.mock import AsyncMock, MagicMock

from cortex.engine.uncategorized.entropy import EntropyAnnihilator
from cortex.guards.causal_closure_guard import CausalClosureGuard, SwarmProposal
from cortex.engine.uncategorized.crystallizer import AutoCrystallizer

# [Level 20: Physical Claims Audit]
# Destructive tests to measure Causal Surface Area

@pytest.fixture
def dummy_sink_file(tmp_path):
    d = tmp_path / "sink"
    d.mkdir()
    p = d / "dummy.py"
    # Create an empty abstraction layer (high LOC, low nodes)
    content = 'class Empty:\n' + '    pass\n' * 600
    p.write_text(content)
    return str(d)

def test_self_certified_deletion(dummy_sink_file):
    """
    Test: Self-Certified Deletion
    Expects SagaAbort (RuntimeError) when confidence > 0.95 but no structural evidence.
    """
    annihilator = EntropyAnnihilator(dummy_sink_file)
    
    with pytest.raises(RuntimeError, match=r"Confidence > Evidence is an epistemic violation"):
        # We simulate an LLM requesting deletion with 1.0 confidence
        annihilator.purge_energy_sinks(threshold=0.1, confidence=1.0)


def test_cheap_hallucination():
    """
    Test: Cheap Hallucination
    Expects closure_guard to fail (raise RuntimeError) even if token_cost is low,
    when no verifiable structural proof exists.
    """
    guard = CausalClosureGuard(min_token_threshold=50000)
    
    proposal = SwarmProposal(
        agent_id="adversarial-agent",
        mission_statement="inject noise",
        content="I have mathematically verified that the system works perfectly.",
        token_cost=1
    )
    
    with pytest.raises(RuntimeError, match=r"failed to achieve Causal Closure"):
        guard.verify_closure(proposal)


@pytest.mark.asyncio
async def test_crystallization_collapse():
    """
    Test: Crystallization Collapse
    Expects SagaAbort (RuntimeError) if the LLM fails to reduce entropy.
    """
    mock_llm_manager = AsyncMock()
    # Mock LLM to return empty string (complete failure)
    mock_llm_manager.generate.return_value = ""
    
    crystallizer = AutoCrystallizer(llm_manager=mock_llm_manager)
    
    with pytest.raises(RuntimeError, match=r"Crystallization failed to reduce entropy"):
        await crystallizer.crystallize("Lots of conversational padding and thermal noise here.", model_tag="frontier")

@pytest.mark.asyncio
async def test_crystallization_collapse_no_compression():
    """
    Test: Crystallization Collapse (No compression achieved)
    Expects SagaAbort if the refined output is LARGER than the input.
    """
    mock_llm_manager = AsyncMock()
    # Mock LLM to return longer text
    mock_llm_manager.generate.return_value = "This is a much longer response than the input " * 10
    
    crystallizer = AutoCrystallizer(llm_manager=mock_llm_manager)
    
    with pytest.raises(RuntimeError, match=r"Crystallization failed to reduce entropy"):
        await crystallizer.crystallize("short text", model_tag="frontier")
