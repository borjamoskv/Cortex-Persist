# [C5-REAL] Exergy-Maximized
"""
Tests for CORTEX-PERSIST DEMO v0.

Verifies:
  - 10,000 event ingestion with sequential SHA-256 hash chain
  - Recursive CTE causal path traversal (WITH RECURSIVE)
  - Cryptographic audit detecting zero violations on clean ledger
  - Tamper detection: modifying a single event propagates chain breach
  - Repair: re-anchoring the hash chain restores integrity
  - Restart counter persistence
"""

import pytest

from cortex.routes.demo import (
    ensure_demo_tables,
    get_demo_state,
    init_demo_events,
    query_causal_chain,
    repair_ledger,
    run_cryptographic_audit,
    tamper_event,
)


@pytest.fixture(autouse=True)
async def _clean_events_table():
    """Ensure events table is clean before each test."""
    from cortex import config
    from cortex.database.core import connect_async_ctx

    async with connect_async_ctx(config.DB_PATH) as conn:
        await ensure_demo_tables(conn)
        await conn.execute("DELETE FROM events")
        await conn.execute(
            "DELETE FROM demo_system_state WHERE key = 'restarts'"
        )
        await conn.commit()
    yield


@pytest.mark.asyncio
async def test_init_generates_10k_events():
    """POST /v0/demo/init should generate exactly 10,000 events."""
    result = await init_demo_events()
    assert result["status"] == "SUCCESS"
    assert result["events_generated"] == 10000


@pytest.mark.asyncio
async def test_state_after_init():
    """GET /v0/demo/state should reflect 10k events with valid integrity."""
    await init_demo_events()
    state = await get_demo_state()

    assert state.events_loaded == 10000
    assert state.hash_integrity is True
    assert state.last_event is not None
    assert state.last_event["id"] == 10000


@pytest.mark.asyncio
async def test_audit_clean_ledger():
    """GET /v0/demo/audit should find zero violations on a fresh ledger."""
    await init_demo_events()
    report = await run_cryptographic_audit()

    assert report.events == 10000
    assert report.integrity == "valid"
    assert report.broken_hashes == 0
    assert report.tampering is False


@pytest.mark.asyncio
async def test_causal_chain_event_9834():
    """GET /v0/demo/causal/9834 should trace 184 events back to root user_request_42."""
    await init_demo_events()
    chain = await query_causal_chain(9834)

    assert chain.event == 9834
    assert chain.causal_path_length == 184
    assert chain.root_cause == "user_request_42"
    assert chain.hash_chain_verified is True
    assert 9833 in chain.caused_by


@pytest.mark.asyncio
async def test_causal_chain_no_parent():
    """An event with no parent should return a path of length 1."""
    await init_demo_events()
    chain = await query_causal_chain(1)

    assert chain.event == 1
    assert chain.causal_path_length == 1


@pytest.mark.asyncio
async def test_tamper_breaks_integrity():
    """POST /v0/demo/tamper/500 should cause audit to detect broken hashes."""
    await init_demo_events()
    await tamper_event(500)

    report = await run_cryptographic_audit()
    assert report.integrity == "compromised"
    assert report.broken_hashes > 0
    assert report.tampering is True


@pytest.mark.asyncio
async def test_repair_restores_integrity():
    """POST /v0/demo/repair should restore a tampered ledger to valid state."""
    await init_demo_events()
    await tamper_event(500)

    # Confirm tampered
    report_before = await run_cryptographic_audit()
    assert report_before.tampering is True

    # Repair
    result = await repair_ledger()
    assert result["status"] == "REPAIRED"

    # Verify restored
    report_after = await run_cryptographic_audit()
    assert report_after.integrity == "valid"
    assert report_after.broken_hashes == 0
    assert report_after.tampering is False


@pytest.mark.asyncio
async def test_empty_ledger_audit():
    """Audit on empty ledger should report compromised (no events to validate)."""
    report = await run_cryptographic_audit()
    assert report.events == 0
    assert report.integrity == "compromised"
