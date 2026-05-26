import pytest
from unittest.mock import AsyncMock, MagicMock
from cortex.verification.oracle import VerificationOracle, VerificationOracleResult


@pytest.fixture
def oracle():
    engine = MagicMock()
    return VerificationOracle(engine=engine)


@pytest.mark.asyncio
async def test_verify_plan_step(oracle):
    res = await oracle.verify("plan_step", {"objective": "Test", "steps": ["step1"]})
    assert res.ok is True
    assert res.verdict == "accepted"
    assert len(res.reasons) == 0

    res_fail = await oracle.verify("plan_step", {})
    assert res_fail.ok is False
    assert res_fail.verdict == "rejected"
    assert "Plan step missing objective." in res_fail.reasons
    assert "Plan step missing steps." in res_fail.reasons


@pytest.mark.asyncio
async def test_verify_tool_result(oracle):
    res = await oracle.verify("tool_result", {"ok": True})
    assert res.ok is True

    res_fail = await oracle.verify("tool_result", {"ok": False})
    assert res_fail.ok is False
    assert "Tool result marked as failed but no error message provided." in res_fail.reasons

    res_fail_with_err = await oracle.verify("tool_result", {"ok": False, "error": "msg"})
    assert res_fail_with_err.ok is True


@pytest.mark.asyncio
async def test_verify_unknown_subject(oracle):
    res = await oracle.verify("unknown", {})
    assert res.ok is True


@pytest.mark.asyncio
async def test_verify_fact_integrity(oracle):
    cursor_mock = AsyncMock()
    cursor_mock.fetchone.return_value = ("content", "hash", "metadata")
    conn_mock = AsyncMock()
    conn_mock.execute.return_value = cursor_mock

    # We need a bit of machinery to mock async with engine.session()
    class AsyncContextManagerMock:
        async def __aenter__(self):
            return conn_mock

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    oracle.engine.session.return_value = AsyncContextManagerMock()

    assert await oracle.verify_fact_integrity(1) is True

    cursor_mock.fetchone.return_value = None
    assert await oracle.verify_fact_integrity(2) is False


@pytest.mark.asyncio
async def test_check_enrichment_status(oracle):
    cursor_mock = AsyncMock()
    cursor_mock.fetchone.return_value = ("processing",)
    conn_mock = AsyncMock()
    conn_mock.execute.return_value = cursor_mock

    class AsyncContextManagerMock:
        async def __aenter__(self):
            return conn_mock

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    oracle.engine.session.return_value = AsyncContextManagerMock()

    assert await oracle.check_enrichment_status(1) == "processing"

    # Test fallback to embeddings
    cursor_mock.fetchone.side_effect = [None, (1,)]
    assert await oracle.check_enrichment_status(2) == "completed"

    cursor_mock.fetchone.side_effect = [None, None]
    assert await oracle.check_enrichment_status(3) == "not_queued"


@pytest.mark.asyncio
async def test_verify_ledger_continuity(oracle):
    # Test verify_ledger path
    oracle.engine.verify_ledger = AsyncMock(return_value={"valid": True})
    assert await oracle.verify_ledger_continuity() is True

    # Reset and test _ledger.audit_integrity_async path
    del oracle.engine.verify_ledger
    oracle.engine._ledger = MagicMock()
    oracle.engine._ledger.audit_integrity_async = AsyncMock(return_value={"valid": True})
    assert await oracle.verify_ledger_continuity() is True

    # Reset and test ledger.audit path
    oracle.engine._ledger = None
    oracle.engine.ledger = MagicMock()
    oracle.engine.ledger.audit = AsyncMock(return_value={"is_valid": True})
    assert await oracle.verify_ledger_continuity() is True

    # Test missing interface
    del oracle.engine.ledger
    assert await oracle.verify_ledger_continuity() is False

    # Test exception handling
    oracle.engine.verify_ledger = AsyncMock(side_effect=Exception("Failed"))
    assert await oracle.verify_ledger_continuity() is False
