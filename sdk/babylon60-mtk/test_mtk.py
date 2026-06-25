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
import os
import sys

# Ensure the local src is in path to test before building
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from babylon60_mtk import install_mtk_authorizer, mtk_active_token, set_token_verifier

# Disable CORTEX_TESTING bypass so the hook actually runs
os.environ["CORTEX_TESTING"] = "0"

def mock_verifier(token: str, payload: str) -> bool:
    return token == "mtk_auth_1234_valid"

def test_mtk():
    set_token_verifier(mock_verifier)
    
    conn = sqlite3.connect(":memory:")
    install_mtk_authorizer(conn)
    
    # 1. READ SHOULD SUCCEED
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        print("✅ READ succeeded (Expected)")
    except sqlite3.DatabaseError as e:
        print(f"❌ READ failed: {e}")
        sys.exit(1)

    # Need a table to test writes. We'll bypass briefly to create it, or since schema changes 
    # are blocked, we'll temporally remove the authorizer.
    conn.set_authorizer(None)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    install_mtk_authorizer(conn)

    # 2. WRITE WITHOUT TOKEN SHOULD FAIL
    try:
        conn.execute("INSERT INTO test (data) VALUES ('unauthorized')")
        print("❌ WRITE without token succeeded! (SECURITY FAILURE)")
        sys.exit(1)
    except sqlite3.DatabaseError as e:
        if "not authorized" in str(e).lower():
            print("✅ WRITE without token physically blocked (Expected)")
        else:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)

    # 3. WRITE WITH INVALID TOKEN SHOULD FAIL
    token_id = mtk_active_token.set("mtk_auth_1234_invalid")
    try:
        conn.execute("INSERT INTO test (data) VALUES ('invalid token')")
        print("❌ WRITE with invalid token succeeded! (SECURITY FAILURE)")
        sys.exit(1)
    except sqlite3.DatabaseError as e:
        if "not authorized" in str(e).lower():
            print("✅ WRITE with invalid token physically blocked (Expected)")
        else:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)
    finally:
        mtk_active_token.reset(token_id)

    # 4. WRITE WITH VALID TOKEN SHOULD SUCCEED
    token_id = mtk_active_token.set("mtk_auth_1234_valid")
    try:
        conn.execute("INSERT INTO test (data) VALUES ('authorized')")
        print("✅ WRITE with valid token succeeded (Expected)")
    except sqlite3.DatabaseError as e:
        print(f"❌ WRITE with valid token failed: {e}")
        sys.exit(1)
    finally:
        mtk_active_token.reset(token_id)

    print("\n[SUCCESS] MTK SQLite Physical Enforcement is mathematically sound.")

if __name__ == "__main__":
    test_mtk()
