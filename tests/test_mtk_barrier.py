import sqlite3
import pytest
import os
from babylon60.engine.mtk_sqlite_authorizer import install_mtk_authorizer, mtk_active_token, mtk_payload_hash

def test_mtk_physical_barrier(monkeypatch):
    monkeypatch.setenv("CORTEX_FORCE_MTK_TESTS", "1")
    monkeypatch.setenv("CORTEX_KERNEL_KEY", "test_key_xyz")
    conn = sqlite3.connect(":memory:")
    
    # 1. Without authorizer, everything works
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test_data (value) VALUES ('unauthorized_1')")
    
    # 2. Install authorizer
    install_mtk_authorizer(conn)
    
    # 3. Structural action should be hard-blocked
    with pytest.raises(sqlite3.DatabaseError) as exc:
        conn.execute("CREATE VIEW test_view AS SELECT * FROM test_data")
    assert "not authorized" in str(exc.value).lower()
    
    # 4. Standard insert without token should be blocked
    with pytest.raises(sqlite3.DatabaseError) as exc:
        conn.execute("INSERT INTO test_data (value) VALUES ('unauthorized_2')")
    assert "not authorized" in str(exc.value).lower()
    
    # 5. Generate and inject valid token
    import cortex_rs
    payload_hash = "mock_payload_hash_123"
    token = cortex_rs.mint_ephemeral_token(payload_hash, os.environ["CORTEX_KERNEL_KEY"])
    
    token_id = mtk_active_token.set(token)
    payload_id = mtk_payload_hash.set(payload_hash)
    
    try:
        # 6. Insert WITH valid token should succeed
        conn.execute("INSERT INTO test_data (value) VALUES ('authorized_1')")
        
        cursor = conn.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        assert count == 2  # unauthorized_1 (before hook) + authorized_1
    finally:
        mtk_active_token.reset(token_id)
        mtk_payload_hash.reset(payload_id)
        
if __name__ == "__main__":
    import unittest.mock
    mock_mp = unittest.mock.MagicMock()
    mock_mp.setenv = lambda k, v: os.environ.update({k: v})
    test_mtk_physical_barrier(mock_mp)
