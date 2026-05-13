from __future__ import annotations

import pytest

from cortex.verification.oracle import VerificationOracle


@pytest.fixture
def oracle():
    from unittest.mock import MagicMock

    return VerificationOracle(engine=MagicMock())


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


@pytest.mark.asyncio
async def test_verify_fallback(oracle):
    result = await oracle.verify(subject="unknown_subject", candidate={})
    assert result.ok is True
    assert result.verdict == "accepted"


import contextlib


class MockCursor:
    def __init__(self, fetchone_result):
        self.fetchone_result = fetchone_result
        self.fetchone_called = False

    async def fetchone(self):
        self.fetchone_called = True
        return self.fetchone_result


class MockSession:
    def __init__(self, fetchone_results):
        self.fetchone_results = fetchone_results
        self.execute_calls = []

    async def execute(self, query, params):
        self.execute_calls.append((query, params))
        return MockCursor(self.fetchone_results.pop(0) if self.fetchone_results else None)


@contextlib.asynccontextmanager
async def mock_session(fetchone_results):
    yield MockSession(fetchone_results)


@pytest.mark.asyncio
async def test_verify_fact_integrity_not_found(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.session = MagicMock(return_value=mock_session([None]))
    assert await oracle.verify_fact_integrity(1) is False


@pytest.mark.asyncio
async def test_verify_fact_integrity_found(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.session = MagicMock(return_value=mock_session([("content", "hash", "{}")]))
    assert await oracle.verify_fact_integrity(1) is True


@pytest.mark.asyncio
async def test_check_enrichment_status_has_job(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.session = MagicMock(return_value=mock_session([("pending",)]))
    assert await oracle.check_enrichment_status(1) == "pending"


@pytest.mark.asyncio
async def test_check_enrichment_status_has_embedding(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.session = MagicMock(return_value=mock_session([None, (1,)]))
    assert await oracle.check_enrichment_status(1) == "completed"


@pytest.mark.asyncio
async def test_check_enrichment_status_not_queued(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.session = MagicMock(return_value=mock_session([None, None]))
    assert await oracle.check_enrichment_status(1) == "not_queued"


@pytest.mark.asyncio
async def test_verify_ledger_continuity_engine_verify_ledger(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.verify_ledger = AsyncMock(return_value={"valid": True})
    assert await oracle.verify_ledger_continuity() is True


@pytest.mark.asyncio
async def test_verify_ledger_continuity_engine_ledger_audit_integrity_async(oracle):
    from unittest.mock import AsyncMock, MagicMock

    del oracle.engine.verify_ledger
    oracle.engine._ledger = MagicMock()
    oracle.engine._ledger.audit_integrity_async = AsyncMock(return_value={"valid": True})
    assert await oracle.verify_ledger_continuity() is True


@pytest.mark.asyncio
async def test_verify_ledger_continuity_engine_ledger_audit(oracle):
    from unittest.mock import AsyncMock, MagicMock

    del oracle.engine.verify_ledger
    oracle.engine._ledger = None
    oracle.engine.ledger = MagicMock()
    oracle.engine.ledger.audit = AsyncMock(return_value={"is_valid": True})
    assert await oracle.verify_ledger_continuity() is True


@pytest.mark.asyncio
async def test_verify_ledger_continuity_engine_no_interface(oracle):
    from unittest.mock import AsyncMock, MagicMock

    del oracle.engine.verify_ledger
    oracle.engine._ledger = None
    del oracle.engine.ledger
    assert await oracle.verify_ledger_continuity() is False


@pytest.mark.asyncio
async def test_verify_ledger_continuity_exception(oracle):
    from unittest.mock import AsyncMock, MagicMock

    oracle.engine.verify_ledger = AsyncMock(side_effect=Exception("Database down"))
    assert await oracle.verify_ledger_continuity() is False
