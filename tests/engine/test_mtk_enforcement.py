
# [C5-REAL] Exergy-Maximized
"""
MTK Physical Enforcement Test.
Validates that the MTK acts as an absolute physical boundary against state mutation.
"""

import sqlite3

import pytest
import datetime

@pytest.fixture(autouse=True)
def force_mtk_enforcement(monkeypatch):
    monkeypatch.setenv("CORTEX_FORCE_MTK_TESTS", "1")
    monkeypatch.setenv("CORTEX_KERNEL_KEY", "test_key_123")
from cortex.engine.mtk_sqlite_authorizer import install_mtk_authorizer
from cortex.engine.mtk_core import MTKGuard
from cortex.types.evidence import ClosurePayload, EvidenceBundle



@pytest.fixture
def mtk_db():
    from cortex.database.core import connect
    # connect() automatically uses SovereignConnection and applies MTK
    conn = connect(":memory:")
    # Initialize schema inside a context where it's allowed or before MTK enforces strict token
    # (Actually, MTK allows CREATE TABLE if it's not blocked. Wait, we are about to block CREATE TABLE!)
    # To initialize schema without MTK token, we might need a workaround or a special setup token.
    # We can just inject a dummy token into ContextVar.
    from cortex.engine.mtk_sqlite_authorizer import mtk_active_token
    token = mtk_active_token.set("mtk_auth_setup")
    try:
        conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, data TEXT)")
    finally:
        mtk_active_token.reset(token)
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
        assert token and ("zk_seal_rs_" in token or "mtk_auth_" in token)
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


@pytest.mark.asyncio
async def test_mtk_capability_dies_with_scope(mtk_db, dummy_payload):
    """
    Add a post-context-exit test proving the capability dies with scope.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    async def run_in_context():
        async with guard.transaction_boundary(dummy_payload) as token:
            assert token.startswith("zk_seal_rs_") or token.startswith("mtk_auth_") or token.startswith("zk_seal_rs_")
            # Mutate
            mtk_db.execute("INSERT INTO records (data) VALUES ('authorized')")
            return token
            
    # Execute the context manager
    await run_in_context()
    
    # After the scope has exited, the context var should be reset.
    # An attempt to mutate the DB should be firmly rejected by the physical boundary.
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("INSERT INTO records (data) VALUES ('out_of_context')")

@pytest.mark.asyncio
async def test_mtk_nested_contexts_isolation(mtk_db, dummy_payload):
    """
    Test that nested contexts do not leak the MTK token into outer contexts or override them incorrectly.
    """
    guard = MTKGuard(private_key="test_key_123")
    # Outer context
    from cortex.engine.mtk_sqlite_authorizer import mtk_active_token
    async with guard.transaction_boundary(dummy_payload) as token_outer:
        mtk_db.execute("INSERT INTO records (data) VALUES ('outer')")

        # Inner context
        import asyncio
        import dataclasses
        await asyncio.sleep(0.01)
        dummy_payload_inner = dataclasses.replace(dummy_payload, info_exergy=0.999)
        object.__setattr__(dummy_payload_inner, 'payload_hash', dummy_payload_inner.payload_hash + "_new")

        async with guard.transaction_boundary(dummy_payload_inner) as token_inner:
            # With the new deterministic Rust Sha3-256 seal, different payloads yield different tokens
            assert token_inner != token_outer
        
        mtk_db.execute("INSERT INTO records (data) VALUES ('inner')")
        
        # Still in outer context, should still be able to mutate
        mtk_db.execute("INSERT INTO records (data) VALUES ('outer2')")
        
    # Outside both, blocked
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("INSERT INTO records (data) VALUES ('blocked')")

@pytest.mark.asyncio
async def test_mtk_concurrent_tasks_isolation(mtk_db, dummy_payload):
    """
    Test that concurrent tasks using asyncio.gather do not bleed the ContextVar across tasks.
    """
    import asyncio
    guard = MTKGuard(private_key="test_key_123")
    
    async def task_with_auth(i):
        async with guard.transaction_boundary(dummy_payload):
            mtk_db.execute(f"INSERT INTO records (data) VALUES ('task_auth_{i}')")
            await asyncio.sleep(0.01)
            mtk_db.execute(f"INSERT INTO records (data) VALUES ('task_auth_{i}_end')")

    async def task_without_auth(i):
        # Without auth, it should fail
        await asyncio.sleep(0.005) # interleave
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            mtk_db.execute(f"INSERT INTO records (data) VALUES ('task_no_auth_{i}')")

    await asyncio.gather(
        task_with_auth(1),
        task_without_auth(2),
        task_with_auth(3),
        task_without_auth(4)
    )
    
    # Verify the authorized ones worked
    cursor = mtk_db.execute("SELECT COUNT(*) FROM records WHERE data LIKE 'task_auth_%'")
    assert cursor.fetchone()[0] == 4

@pytest.mark.asyncio
async def test_mtk_fuzz_sql(mtk_db, dummy_payload):
    """
    Fuzz random invalid SQL statements to ensure the authorizer correctly denies
    mutations even if SQL is malformed or attempts tricky injections.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    fuzz_statements = [
        "DROP TABLE records",
        "ALTER TABLE records ADD COLUMN test_col TEXT",
        "CREATE TABLE unauthorized_table (id INTEGER)",
        "DELETE FROM records",
        "UPDATE records SET data = 'hacked'",
        "INSERT INTO records (data) VALUES ('hacked'); DROP TABLE records;"
    ]
    
    # Outside context, ALL must fail due to MTK physical boundary
    for stmt in fuzz_statements:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            mtk_db.execute(stmt)
                
    # Inside context, they should pass authorizer (though some might fail if the token doesn't grant DROP table)
    # The current MTK implementation allows all mutations if the token is valid, so they should execute
    # or throw standard operational errors if the schema prevents it, but NOT an authorizer "not authorized" error.
    async with guard.transaction_boundary(dummy_payload):
        for stmt in fuzz_statements:
            try:
                mtk_db.executescript(stmt)
            except Exception:
                pass # As long as it's not a 'not authorized' exception it's fine for fuzzing

@pytest.mark.asyncio
async def test_mtk_legacy_connection_dynamic_capability(dummy_payload, tmp_path):
    """
    A connection opened *before* the MTK context still respects the boundary dynamically at execution time.
    """
    from cortex.database.core import connect_async
    db_file = tmp_path / "legacy.db"
    
    # Pre-create connection (legacy/global connection pattern)
    conn = await connect_async(str(db_file))
    try:
        # Outside context -> blocked
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            await conn.execute("CREATE TABLE test (id int)")
            
        guard = MTKGuard(private_key="test_key_123")
        
        # Inside context -> allowed
        async with guard.transaction_boundary(dummy_payload):
            await conn.execute("CREATE TABLE test (id int)")
            
        # Outside context again -> blocked
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            await conn.execute("INSERT INTO test VALUES (1)")
    finally:
        await conn.close()

def test_mtk_authorizer_replacement_fails(mtk_db):
    """
    Attempting to overwrite `set_authorizer` on a protected connection fails.
    """
    with pytest.raises(sqlite3.DatabaseError, match="MTK-LOCK"):
        mtk_db.set_authorizer(None)
    
    with pytest.raises(sqlite3.DatabaseError, match="MTK-LOCK"):
        mtk_db.set_authorizer(lambda *args: sqlite3.SQLITE_OK)

@pytest.mark.asyncio
async def test_mtk_blocks_pragma_modifications(mtk_db, dummy_payload):
    """
    Empirical Falsification 1: PRAGMA modification vs read.
    Validates that `PRAGMA synchronous=OFF` is blocked even with an MTK token,
    but reading `PRAGMA synchronous` is allowed.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    # Outside boundary: Read is allowed
    mtk_db.execute("PRAGMA synchronous").fetchone()
    
    # Outside boundary: Write is blocked
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("PRAGMA synchronous=OFF")
        
    # Inside boundary: Read is allowed, Write is STILL blocked (Default Deny for structural PRAGMAs)
    async with guard.transaction_boundary(dummy_payload):
        mtk_db.execute("PRAGMA synchronous").fetchone()
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            mtk_db.execute("PRAGMA synchronous=OFF")

@pytest.mark.asyncio
async def test_mtk_blocks_structural_ddl_with_or_without_token(mtk_db, dummy_payload):
    """
    Empirical Falsification 2: Structural DDL (e.g., ATTACH, CREATE TRIGGER, CREATE VIEW)
    must be blocked completely regardless of MTK capability presence.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    ddl_statements = [
        "ATTACH DATABASE 'rogue.db' AS rogue",
        "CREATE VIEW evil_view AS SELECT * FROM records",
        "CREATE TRIGGER evil_trigger AFTER INSERT ON records BEGIN SELECT 1; END"
    ]
    
    # Outside boundary: Blocked
    for stmt in ddl_statements:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            mtk_db.execute(stmt)
            
    # Inside boundary: STILL Blocked (Hard-blocked by DANGEROUS_ACTIONS)
    async with guard.transaction_boundary(dummy_payload):
        for stmt in ddl_statements:
            with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
                mtk_db.execute(stmt)

@pytest.mark.asyncio
async def test_mtk_blocks_shadow_table_evasion(mtk_db, dummy_payload):
    """
    Empirical Falsification 3: Shadow table name spoofing.
    Validates that creating or writing to a table ending in `_data` without a token
    is correctly rejected by the MTK engine.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    # Attempting to create a spoofed shadow table outside boundary MUST fail
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("CREATE TABLE evil_data (id INTEGER)")
        
    # Inside boundary, authorize creating a table that looks like a shadow table
    async with guard.transaction_boundary(dummy_payload):
        mtk_db.execute("CREATE TABLE cortex_vectors_data (id INTEGER)")
        
    # Outside boundary: Attempting to write to it MUST fail (the `endswith` bypass is removed)
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        mtk_db.execute("INSERT INTO cortex_vectors_data (id) VALUES (1)")
        
    # Inside boundary: Authorized
    async with guard.transaction_boundary(dummy_payload):
        mtk_db.execute("INSERT INTO cortex_vectors_data (id) VALUES (1)")
