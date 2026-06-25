import pytest
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from babylon60.engine.mtk_sqlite_authorizer import install_mtk_authorizer, mtk_active_token

def test_mtk_memory_taint_blocks_stochastic_module(monkeypatch):
    """Test that MTK blocks DB writes if executed from a stochastic module, even with token."""
    
    conn = sqlite3.connect(":memory:")
    install_mtk_authorizer(conn)
    
    # We create a dummy table. Schema changes are hard-blocked by MTK if not in SAFE_ACTIONS
    # wait, we need to bypass MTK to create the table or use the testing override.
    monkeypatch.setenv("CORTEX_TESTING", "1")
    monkeypatch.setenv("CORTEX_FORCE_MTK_TESTS", "1")
    
    # Temporarily disable authorizer to setup
    conn.set_authorizer(None)
    conn.execute("CREATE TABLE test_data (id INTEGER, value TEXT)")
    conn.commit()
    
    # Re-enable
    install_mtk_authorizer(conn)
    
    token_id = mtk_active_token.set("mtk_auth_dummy_token_123")
    
    # Try inserting. It should succeed normally since we have a token
    try:
        conn.execute("INSERT INTO test_data (id, value) VALUES (1, 'safe')")
        conn.commit()
    except sqlite3.DatabaseError as e:
        pytest.fail(f"Insert failed unexpectedly: {e}")
        
    # Now simulate being in a stochastic module by injecting into sys.modules and setting __name__
    def stochastic_injection_attempt():
        # Fake being a stochastic module
        globals()["__name__"] = "babylon60.engine.synthesis.fake"
        try:
            conn.execute("INSERT INTO test_data (id, value) VALUES (2, 'stochastic')")
            conn.commit()
            return False
        except sqlite3.DatabaseError:
            return True
        finally:
            globals()["__name__"] = "tests.engine.test_mtk_memory_taint"
            
    blocked = stochastic_injection_attempt()
    assert blocked is True, "MTK failed to block stochastic memory injection"

    mtk_active_token.reset(token_id)


def test_mtk_memory_taint_blocks_tainted_variable(monkeypatch):
    """Test that MTK blocks DB writes if any variable in the stack has __taint__ attribute."""
    
    monkeypatch.setenv("CORTEX_TESTING", "1")
    monkeypatch.setenv("CORTEX_FORCE_MTK_TESTS", "1")

    conn = sqlite3.connect(":memory:")
    install_mtk_authorizer(conn)
    
    # Temporarily disable authorizer to setup
    conn.set_authorizer(None)
    conn.execute("CREATE TABLE IF NOT EXISTS test_data (id INTEGER, value TEXT)")
    conn.commit()
    install_mtk_authorizer(conn)
    
    token_id = mtk_active_token.set("mtk_auth_dummy_token_123")
    
    class TaintedData:
        __taint__ = True
        
    def execute_with_taint():
        tainted_obj = TaintedData()  # This will be in local variables
        try:
            conn.execute("INSERT INTO test_data (id, value) VALUES (3, 'tainted')")
            conn.commit()
            return False
        except sqlite3.DatabaseError:
            return True
            
    blocked = execute_with_taint()
    assert blocked is True, "MTK failed to block memory tainted variable injection"

    mtk_active_token.reset(token_id)
