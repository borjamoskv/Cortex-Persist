# [C5-REAL] Exergy-Maximized
"""
Verification tests for Autodidact Pipeline Refinement (Epoch 11).
Tests the Yield Inversion for Vulnerabilities (Bounty Exergy).
"""

import pytest

from cortex.extensions.swarm.autodidact_actuator import autodidact_ingest


@pytest.mark.asyncio
async def test_normal_epistemic_failure_purges():
    """Test that a normal script failing an assertion is PURGED."""
    source_code = "assert 1 == 0, 'Logic error'"
    metadata = {"intent": "learn"}

    result = await autodidact_ingest(source_code, expected_yield_gain=1.0, metadata=metadata)

    assert result["action"] == "PURGE"
    assert result["reason"] == "LOGIC_ERROR"
    assert "AssertionError" in result["details"]


@pytest.mark.asyncio
async def test_bounty_poc_success_crystallizes():
    """Test that a bounty PoC failing an assertion yields massive exergy."""
    source_code = "assert 1 == 0, 'Vulnerability triggered'"
    metadata = {"intent": "bounty_poc"}

    result = await autodidact_ingest(source_code, expected_yield_gain=1.0, metadata=metadata)

    assert result["action"] == "CRYSTALLIZE"
    assert result["resonance"] == 1000.0


@pytest.mark.asyncio
async def test_bounty_poc_other_failure_purges():
    """Test that a bounty PoC with a Syntax/TypeError still purges."""
    source_code = "1 + 'a'"  # TypeError
    metadata = {"intent": "bounty_poc"}

    result = await autodidact_ingest(source_code, expected_yield_gain=1.0, metadata=metadata)

    assert result["action"] == "PURGE"
    assert result["reason"] == "LOGIC_ERROR"
    assert "TypeError" in result["details"]
