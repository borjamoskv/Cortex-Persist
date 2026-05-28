import json
from unittest.mock import AsyncMock, patch

import pytest

from cortex.extensions.swarm.crystal_synthesis import synthesize_crystals
from cortex.utils.result import Ok


@pytest.mark.asyncio
@patch("cortex.extensions.swarm.crystal_synthesis._get_synthesis_router")
async def test_semantic_crystal_merge_preserves_unique_details(mock_get_router):
    """Verify that synthesizing two highly redundant crystals preserves unique details.

    Axiom Ω₂: Entropic Asymmetry. Ensure noise is reduced without loss of signal.
    """

    # Mock the router output to simulate LLM success
    mock_router = AsyncMock()
    mock_response = json.dumps(
        {
            "fused_content": "# Sovereign Agent Architecture (v8.0)\nAgents must be sovereign, operating asynchronously and decoupled from their underlying LLM providers (OpenAI, Google). They use an Immunitas Membrane for security, specifically intercepting MCP tool payloads. The default memory is SQLite.",
            "merged_entities": ["Sovereign Agent Architecture", "Immunitas Membrane"],
            "synthesis_logic": "Combined core concepts while retaining unique versioning and technical specifics from both crystals.",
        }
    )
    mock_router.execute_resilient.return_value = Ok(mock_response)
    mock_get_router.return_value = mock_router

    crystal_a = (
        "# Sovereign Agent Architecture\n"
        "Agents must be sovereign, operating asynchronously and decoupled from their underlying "
        "LLM providers. They use an Immunitas Membrane for security. The default memory "
        "is SQLite."
    )

    crystal_b = (
        "# Sovereign Agent Architecture (v8.0)\n"
        "Agents must operate asynchronously and decoupled from providers (OpenAI, Google). "
        "They use an Immunitas Membrane for security, specifically intercepting MCP tool payloads. "
        "The default memory is SQLite."
    )

    result = await synthesize_crystals(crystal_a, crystal_b, context="Test Merge")

    assert "error" not in result, f"Synthesis failed: {result.get('error')}"

    fused_content = result.get("fused_content", "")
    assert fused_content, "Fused content is empty"

    fused_lower = fused_content.lower()

    # Must contain the core idea
    assert "sovereign" in fused_lower or "soberan" in fused_lower, "Lost core concept: sovereign"
    assert "asynchron" in fused_lower or "asíncron" in fused_lower, (
        "Lost core concept: asynchronous"
    )

    # Must contain unique detail from Crystal A
    # (In this simple test, both are fairly similar, but let's check for "LLM")
    assert "llm" in fused_lower, "Lost unique detail from A: 'LLM providers'"

    # Must contain unique detail from Crystal B
    assert "v8.0" in fused_lower, "Lost unique detail from B: 'v8.0'"
    assert "openai" in fused_lower, "Lost unique detail from B: 'OpenAI'"
    assert "mcp" in fused_lower, "Lost unique detail from B: 'MCP tool payloads'"

    # Check if the JSON was parsed properly returning metadata
    assert "merged_entities" in result, "Did not return JSON format with merged_entities"
    assert "synthesis_logic" in result, "Did not return JSON format with synthesis_logic"
