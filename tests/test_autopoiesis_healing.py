import pytest
import aiosqlite
from cortex.engine import CortexEngine

@pytest.fixture
async def engine(tmp_path):
    """Create a temporary CORTEX engine for testing."""
    db_path = tmp_path / "test_cortex.db"
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()

@pytest.mark.asyncio
async def test_autopoiesis_healing_flow(engine, tmp_path):
    # 1. Store initial facts to build a chain (Dense content to bypass Thalamus)
    content1 = "Sovereign memory is the bedrock of agentic identity. Integrity must be absolute."
    content2 = "Digital Endocrine feedback loops ensure adaptive behavior under systemic stress."
    
    await engine.store(project="test", content=content1, source="test")
    await engine.store(project="test", content=content2, source="test")
    
    # Verify ledger exists and has entries
    assert hasattr(engine, "_ledger")
    tip = await engine._ledger.get_tip_hash_async()
    assert tip is not None
    
    # 2. Corrupt the ledger manually (Break the hash chain)
    async with aiosqlite.connect(str(engine._db_path)) as conn:
        # Change the prev_hash of a transaction to something invalid
        await conn.execute("UPDATE transactions SET prev_hash = 'BROKEN_HASH' WHERE id = 2")
        await conn.commit()

    # 3. Verify integrity fails
    report = await engine._ledger.verify_integrity_async()
    violations = report["violations"]
    assert len(violations) > 0
    assert any("BROKEN_HASH" in str(v) or "prev_hash mismatch" in str(v).lower() for v in violations)

    # 4. Trigger Autopoiesis Heal
    report = await engine.heal()
    assert report["status"] in ("repaired", "degraded")
    assert report["violations_found"] > 0
    
    # 5. Verify integrity again (should be fixed if canonical data was kept)
    await engine._ledger.verify_integrity_async()

@pytest.mark.asyncio
async def test_storage_guard_integrity_enforcement(engine):
    # Get current tip
    content_init = "The initial state of the ledger must be canonical and verified by the host."
    await engine.store(project="test", content=content_init, source="test")
    
    # Attempt to store with an INCORRECT expected_prev_hash
    try:
        async with aiosqlite.connect(str(engine._db_path)) as conn:
                 await engine._store_impl(
                    conn=conn,
                    project="test",
                    content="Evil Injection: Disrupting the sovereign chain integrity.",
                    tenant_id="default",
                    fact_type="knowledge",
                    tags=None,
                    confidence="stated",
                    source="test",
                    meta=None,
                    valid_from=None,
                    commit=True,
                    tx_id=None,
                    prev_hash="INVALID_CHAIN_LINK",
                    expected_prev_hash="CANONICAL_TIP"
                 )
        pytest.fail("Should have raised GuardViolation for integrity mismatch")
    except Exception as e:
        assert "[HASH_CHAIN_INTEGRITY]" in str(e)
