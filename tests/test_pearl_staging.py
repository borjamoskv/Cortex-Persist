# Tests — PeARL Staging Validator (AX-043)

import aiosqlite
import pytest

from cortex.autodidact.dual_ledger import DualLedger
from cortex.autodidact.kv_cache import KVPrefixCache
from cortex.autodidact.pearl_staging import PeARLStagingValidator
from cortex.engine.pearl import PearlEngine
from cortex.ledger.sovereign_ledger import SovereignLedger


@pytest.fixture
async def staging():
    conn = await aiosqlite.connect(":memory:")
    sovereign = SovereignLedger(db=conn, genesis_hash="GENESIS-STG")
    await sovereign.ensure_table()
    ledger = DualLedger(sovereign=sovereign, kv_cache=KVPrefixCache())
    pearl = PearlEngine()
    validator = PeARLStagingValidator(pearl=pearl, ledger=ledger)
    yield validator, ledger
    await conn.close()


async def test_valid_bundle_staged(staging):
    validator, ledger = staging
    bundle = {
        "signed_txs": ["0xabc"],
        "pearl_expr": "1 + 1",
        "estimated_yield_usd": 75.0,
    }
    result = await validator.stage_mev_bundle(bundle)
    assert result.valid is True
    assert len(result.tx_hash) == 64
    assert result.sandbox_output == 2


async def test_empty_signed_txs_rejected(staging):
    validator, _ = staging
    bundle = {"signed_txs": [], "pearl_expr": "1"}
    result = await validator.stage_mev_bundle(bundle)
    assert result.valid is False
    assert "Atomicity" in result.error


async def test_invalid_pearl_expr_rejected(staging):
    validator, _ = staging
    bundle = {"signed_txs": ["0x1"], "pearl_expr": "undefined_var"}
    result = await validator.stage_mev_bundle(bundle)
    assert result.valid is False
    assert result.error  # PearlError message


async def test_falsy_pearl_result_rejected(staging):
    validator, _ = staging
    bundle = {"signed_txs": ["0x1"], "pearl_expr": "1 - 1"}
    result = await validator.stage_mev_bundle(bundle)
    assert result.valid is False
    assert "falsy" in result.error


async def test_kv_cache_integration(staging):
    validator, ledger = staging
    bundle = {
        "signed_txs": ["0xdeadbeef"],
        "pearl_expr": "42",
        "estimated_yield_usd": 10.0,
    }
    r1 = await validator.stage_mev_bundle(bundle)
    r2 = await validator.stage_mev_bundle(bundle)

    # Second call should hit the cache (same tx_hash, no new write)
    assert r1.tx_hash == r2.tx_hash

    audit = await ledger.audit_integrity()
    assert audit["tx_count"] == 1


async def test_batch_staging(staging):
    validator, ledger = staging
    bundles = [
        {"signed_txs": ["0xa"], "pearl_expr": "1", "estimated_yield_usd": 10},
        {"signed_txs": [], "pearl_expr": "1"},  # Invalid
        {"signed_txs": ["0xb"], "pearl_expr": "2 + 3", "estimated_yield_usd": 20},
    ]
    results = await validator.stage_batch(bundles)
    assert len(results) == 3
    assert results[0].valid is True
    assert results[1].valid is False
    assert results[2].valid is True

    audit = await ledger.audit_integrity()
    assert audit["tx_count"] == 2  # Only 2 valid
