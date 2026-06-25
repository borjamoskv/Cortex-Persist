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


def cb(*args): return sqlite3.SQLITE_DENY
db = sqlite3.connect(":memory:")
db.set_authorizer(cb)
try:
    db.execute("CREATE TABLE t (id int)")
except Exception as e:
    print(f"EXCEPTION: {type(e)}")
    print(f"MESSAGE: {e}")
