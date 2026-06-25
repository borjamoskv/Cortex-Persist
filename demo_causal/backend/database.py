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

DB_PATH = os.path.join(os.path.dirname(__file__), 'causal_demo.db')

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            type TEXT,
            actor TEXT,
            payload TEXT,
            parent_event INTEGER,
            prev_hash TEXT,
            event_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
