# Tests — Dual Ledger (AX-041)

import json

import aiosqlite
import pytest

from cortex.autodidact.dual_ledger import DualLedger, TxType
from cortex.autodidact.kv_cache import KVPrefixCache
from cortex.ledger.sovereign_ledger import SovereignLedger


@pytest.fixture
async def dual():
    """In-memory DualLedger wired to a real SovereignLedger."""
    conn = await aiosqlite.connect(":memory:")
    sovereign = SovereignLedger(db=conn, genesis_hash="GENESIS-TEST")
    await sovereign.ensure_table()
    kv = KVPrefixCache(max_size=64)
    ledger = DualLedger(sovereign=sovereign, kv_cache=kv)
    yield ledger
    await conn.close()


async def test_single_chain_sequential_hashes(dual: DualLedger):
    """CAPITAL and KNOWLEDGE entries share prevhash linkage."""
    h1 = await dual.record_capital("ouro", "bounty", {"exergy_usd": 100})
    h2 = await dual.record_knowledge("millennium", "proof", {"theorem": "Riemann"})
    h3 = await dual.record_capital("ouro", "arb", {"exergy_usd": 50})

    assert h1 != h2 != h3
    assert len(h1) == 64  # SHA-256 hex

    # Chain integrity
    audit = await dual.audit_integrity()
    assert audit["valid"] is True
    assert audit["tx_count"] == 3


async def test_kv_cache_dedup(dual: DualLedger):
    """Identical capital payloads return cached hash, no new tx."""
    detail = {"signed_txs_count": 3, "exergy_usd": 42}
    h1 = await dual.record_capital("ouro", "mev_staged", detail)
    h2 = await dual.record_capital("ouro", "mev_staged", detail)

    assert h1 == h2  # Cache hit

    audit = await dual.audit_integrity()
    assert audit["tx_count"] == 1  # Only one actual tx


async def test_skip_cache_forces_new_tx(dual: DualLedger):
    """skip_cache=True always writes a new entry."""
    detail = {"data": "same"}
    h1 = await dual.record_capital("ouro", "act", detail, skip_cache=False)
    h2 = await dual.record_capital("ouro", "act", detail, skip_cache=True)

    assert h1 != h2


async def test_audit_dual_stream_metrics(dual: DualLedger):
    """audit_dual reports per-stream counts and exergy balance."""
    await dual.record_capital("ouro", "bounty", {"exergy_usd": 200}, skip_cache=True)
    await dual.record_capital("ouro", "arb", {"exergy_usd": 50}, skip_cache=True)
    await dual.record_knowledge("mill", "proof", {"theorem": "PvsNP"}, skip_cache=True)

    report = await dual.audit_dual()
    assert report["valid"] is True
    assert report["capital_count"] == 2
    assert report["knowledge_count"] == 1
    assert report["exergy_balance"] == 250.0
    assert "cache_stats" in report


async def test_chain_break_detected(dual: DualLedger):
    """Tampering with a hash breaks audit_integrity."""
    await dual.record_capital("p", "a", {"x": 1}, skip_cache=True)
    await dual.record_knowledge("p", "b", {"y": 2}, skip_cache=True)

    # Tamper the first tx hash
    async with dual.sovereign._acquire_conn() as conn:
        await conn.execute(
            "UPDATE transactions SET hash = 'TAMPERED' WHERE id = 1"
        )
        await conn.commit()

    audit = await dual.audit_integrity()
    assert audit["valid"] is False
    assert any(v["type"] == "CHAIN_BREAK" for v in audit["violations"])
