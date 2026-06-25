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


def _migration_001_add_updated_at(conn: sqlite3.Connection):
    """Add updated_at column to facts table if missing."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN updated_at TEXT")
        logger.info("Migration 001: Added 'updated_at' column to facts")


def _migration_002_add_indexes(conn: sqlite3.Connection):
    """Add performance indexes."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_project_active ON facts(project, valid_until)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_created ON facts(created_at DESC)")
    logger.info("Migration 002: Added performance indexes")


def _migration_003_enable_wal(conn: sqlite3.Connection):
    """Enable WAL mode for better concurrent read performance."""
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("Migration 003: Enabled WAL journal mode")


def _migration_004_vector_index(conn: sqlite3.Connection):
    """Create pruned_embeddings table for embedding lifecycle management.

    NOTE: The original migration attempted ``CREATE INDEX USING ivf0`` which
    is invalid sqlite-vec syntax (vec0 virtual tables do not support secondary
    indexes).  Replaced with a pruning metadata table that stores SHA-256
    hashes of archived embeddings for cold-storage verification.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pruned_embeddings (
            fact_id     INTEGER PRIMARY KEY,
            hash        TEXT NOT NULL,
            dimension   INTEGER NOT NULL DEFAULT 384,
            pruned_at   TEXT NOT NULL DEFAULT (datetime('now')),
            reason      TEXT DEFAULT 'deprecated'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pruned_at ON pruned_embeddings(pruned_at)")
    logger.info("Migration 004: Created pruned_embeddings table (replaces dead IVF index)")


def _migration_005_fts5_setup(conn: sqlite3.Connection):
    """Setup FTS5 virtual table for high-performance text search."""
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5("
        "    content, project, tags, fact_type"
        ")"
    )
    logger.info("Migration 005: Initialized FTS5 search table")
