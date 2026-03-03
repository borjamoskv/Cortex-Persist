"""Tests for ImmuneArbiter (Ωv3).

Verifies the 5-filter membrane logic.
"""

import pytest

from cortex.immune.arbiter import ImmuneArbiter, Verdict


@pytest.mark.asyncio
async def test_immune_arbiter_low_risk_pass():
    arbiter = ImmuneArbiter()
    plan = {"actions": [{"type": "read", "path": "file.py"}]}
    result = await arbiter.triage("Read file content", plan, confidence=0.99)

    assert result.verdict == Verdict.PASS
    assert result.triage_score >= 85
    assert result.blast_radius == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_immune_arbiter_high_risk_hold():
    arbiter = ImmuneArbiter()
    plan = {"actions": [{"type": "push", "remote": "origin"}]}
    result = await arbiter.triage("Push code to prod", plan, confidence=0.5)

    assert result.verdict == Verdict.HOLD
    assert any(
        "F1_REVERSIBILITY" in r or "F5_CONFIDENCE" in r
        for r in result.risks_assumed
    )
    assert result.blast_radius == pytest.approx(75.0)


@pytest.mark.asyncio
async def test_immune_arbiter_entropy_hold():
    arbiter = ImmuneArbiter()
    plan = {
        "actions": [{"type": "write"}],
        "added_lines": 500,
        "removed_lines": 0,
    }
    result = await arbiter.triage("Massive feature add", plan, confidence=0.9)

    assert result.verdict == Verdict.HOLD
    assert any("F4_ENTROPY" in r for r in result.risks_assumed)


@pytest.mark.asyncio
async def test_immune_arbiter_block_on_combined_risk():
    """A deploy with zero confidence should HOLD (or BLOCK if filters escalate)."""
    arbiter = ImmuneArbiter()
    plan = {
        "actions": [{"type": "deploy", "target": "production"}],
        "added_lines": 1000,
        "removed_lines": 0,
        "new_files": 5,
    }
    result = await arbiter.triage("Deploy to prod", plan, confidence=0.01)

    # Multiple filters should flag this
    assert result.verdict in (Verdict.HOLD, Verdict.BLOCK)
    assert len(result.risks_assumed) >= 2
    assert result.immunity_certificate is False


@pytest.mark.asyncio
async def test_immune_arbiter_safe_refactor_pass():
    """A net-negative entropy refactor with high confidence should PASS."""
    arbiter = ImmuneArbiter()
    plan = {
        "actions": [{"type": "write"}],
        "added_lines": 10,
        "removed_lines": 50,
        "fixme_resolved": 3,
    }
    result = await arbiter.triage("Refactor cleanup", plan, confidence=0.95)

    assert result.verdict == Verdict.PASS
    assert result.immunity_certificate is True
