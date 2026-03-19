from __future__ import annotations

import pytest

from cortex.verification.oracle import VerificationOracle


@pytest.fixture
def oracle():
    return VerificationOracle()


@pytest.mark.asyncio
async def test_verify_plan_step_valid(oracle):
    candidate = {"objective": "Plan the attack", "steps": ["Gather intel"]}
    result = await oracle.verify(subject="plan_step", candidate=candidate)
    assert result.ok is True
    assert result.verdict == "accepted"


@pytest.mark.asyncio
async def test_verify_plan_step_invalid(oracle):
    candidate = {"not_objective": "invalid"}
    result = await oracle.verify(subject="plan_step", candidate=candidate)
    assert result.ok is False
    assert result.verdict == "rejected"
    assert "Plan step missing objective." in result.reasons


@pytest.mark.asyncio
async def test_verify_tool_result_valid(oracle):
    candidate = {"ok": True, "result": {"output": "success"}}
    result = await oracle.verify(subject="tool_result", candidate=candidate)
    assert result.ok is True


@pytest.mark.asyncio
async def test_verify_tool_result_invalid(oracle):
    candidate = {"ok": False}  # Missing error
    result = await oracle.verify(subject="tool_result", candidate=candidate)
    assert result.ok is False
    assert "Tool result marked as failed but no error message provided." in result.reasons


@pytest.mark.asyncio
async def test_verify_code_formal_check(oracle):
    # This should trigger SovereignVerifier
    candidate = {"code": "print('hello')", "ok": True}
    result = await oracle.verify(subject="tool_result", candidate=candidate)
    # Default verifier (no z3) should return ok=True for simple prints
    assert result.ok is True
