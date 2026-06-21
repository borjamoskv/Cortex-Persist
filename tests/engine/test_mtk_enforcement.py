# [C5-REAL] Exergy-Maximized
"""
MTK Physical Enforcement Test.
Validates that the MTK acts as an absolute physical boundary against state mutation.
"""

import sqlite3
import pytest
import datetime
from cortex.engine.mtk_sqlite_authorizer import install_mtk_authorizer
from cortex.engine.mtk_core import MTKGuard
from cortex.types.evidence import ClosurePayload, EvidenceBundle

@pytest.fixture
def mtk_db():
    conn = sqlite3.connect(":memory:")
    # Initialize schema so authorizer doesn't block it (we ignore sqlite_ schemas in the hook)
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, data TEXT)")
    
    # Install the physical barrier
    install_mtk_authorizer(conn)
    return conn

@pytest.fixture
def dummy_payload():
    evidence = EvidenceBundle.forge(
        query="dummy",
        sources=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    )
    return ClosurePayload.seal(
        claims=[{"claim": "test"}],
        evidence=evidence,
        verdict=True
    )

def test_mtk_blocks_unauthorized_mutation(mtk_db):
    """
    Attempt to mutate state directly without an MTK token.
    This simulates a "Silent Bypass" attempt. The SQLite engine must physically reject it.
    """
    with pytest.raises(sqlite3.DatabaseError) as exc_info:
        mtk_db.execute("INSERT INTO records (data) VALUES ('unauthorized')")
        
    assert "not authorized" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_mtk_allows_authorized_mutation(mtk_db, dummy_payload):
    """
    Attempt to mutate state through the MTK physical boundary.
    The mutation must succeed.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    async with guard.transaction_boundary(dummy_payload) as token:
        assert token.startswith("mtk_auth_")
        # Now authorized, this should not raise DatabaseError
        cursor = mtk_db.execute("INSERT INTO records (data) VALUES ('authorized')")
        assert cursor.rowcount == 1
        
    # Once outside the boundary, mutation should be blocked again
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("INSERT INTO records (data) VALUES ('unauthorized_after')")

@pytest.mark.asyncio
async def test_mtk_rejects_invalid_payload():
    """
    MTK must reject negative verdicts immediately without minting a token.
    """
    guard = MTKGuard(private_key="test_key_123")
    evidence = EvidenceBundle.forge(
        query="dummy",
        sources=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    )
    payload_negative = ClosurePayload.seal(
        claims=[{"claim": "test"}],
        evidence=evidence,
        verdict=False  # Invalid causality
    )
    
    with pytest.raises(ValueError, match="MTK-REJECT"):
        async with guard.transaction_boundary(payload_negative):
            pass

@pytest.mark.asyncio
async def test_mtk_factory_leak(tmp_path):
    """
    Nasty negative test: Prove that importing the standard connection factory 
    yields a connection that is ALREADY locked down by MTK.
    """
    from cortex.database.core import connect_async, connect
    db_file = tmp_path / "factory_leak.db"
    
    # Pre-create schema so authorizer doesn't trip on internal initializations
    sync_conn = sqlite3.connect(str(db_file))
    sync_conn.execute("CREATE TABLE factory_records (id INTEGER PRIMARY KEY, data TEXT)")
    sync_conn.close()

    # Get connection from production factory
    conn = await connect_async(str(db_file))
    
    try:
        # We know the schema, the table, the exact SQL, but we DO NOT have an MTK token.
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            await conn.execute("INSERT INTO factory_records (data) VALUES ('leaked')")
            
        # Same for sync factory
        sync_conn_prod = connect(str(db_file))
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            sync_conn_prod.execute("INSERT INTO factory_records (data) VALUES ('leaked_sync')")
            
    finally:
        await conn.close()


import math
import cortex_rs
from cortex.engine.entropy_core import calculate_entropy_b60

def test_rust_ffi_entropy_b60_contract():
    """
    Test Rust FFI contract comparing Python and Rust BABYLON-60 outputs on the same inputs.
    """
    data = b"cortex-persist physical enforcement"
    
    # Calculate in Python
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    
    entropy_py = 0.0
    for c in counts:
        if c > 0:
            p = c / len(data)
            entropy_py -= p * math.log2(p)
            
    # Scale to Babylon60 format
    expected_b60_value = int(round(entropy_py * 216000))
    
    # Calculate via Rust FFI
    b60_rust = calculate_entropy_b60(data)
    
    assert b60_rust.get_value() == expected_b60_value

@pytest.mark.asyncio
async def test_mtk_capability_dies_with_scope(mtk_db, dummy_payload):
    """
    Add a post-context-exit test proving the capability dies with scope.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    async def run_in_context():
        async with guard.transaction_boundary(dummy_payload) as token:
            assert token.startswith("mtk_auth_")
            mtk_db.execute("INSERT INTO records (data) VALUES ('in_context')")
            return token
            
    # Execute the context manager
    await run_in_context()
    
    # After the scope has exited, the context var should be reset.
    # An attempt to mutate the DB should be firmly rejected by the physical boundary.
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("INSERT INTO records (data) VALUES ('out_of_context')")
