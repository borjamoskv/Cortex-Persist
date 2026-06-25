# [C5-REAL] Exergy-Maximized
import logging
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

logger = logging.getLogger("cortex")


def _migration_031_agent_eroi(conn: sqlite3.Connection):
    """Implement subagent EROI and task reputation tracking table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_tasks_eroi (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id        TEXT NOT NULL REFERENCES agents(id),
            task_type       TEXT NOT NULL,
            exergy_yield    REAL NOT NULL,
            entropy_paid    REAL NOT NULL,
            tokens_spent    INTEGER NOT NULL DEFAULT 0,
            eroi_score      REAL NOT NULL,
            status          TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_eroi_agent_task ON agent_tasks_eroi(agent_id, task_type);
    """)
    logger.info("Migration 031: Created 'agent_tasks_eroi' table and index")
