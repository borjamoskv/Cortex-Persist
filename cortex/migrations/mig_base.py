import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_001_add_updated_at(conn: sqlite3.Connection):
    """Add updated_at column to facts table if missing."""
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()
    }
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN updated_at TEXT")
        logger.info("Migration 001: Added 'updated_at' column to facts")


def _migration_002_add_indexes(conn: sqlite3.Connection):
    """Add performance indexes."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_project_active "
        "ON facts(project, valid_until)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_type "
        "ON facts(fact_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_created "
        "ON facts(created_at DESC)"
    )
    logger.info("Migration 002: Added performance indexes")


def _migration_003_enable_wal(conn: sqlite3.Connection):
    """Enable WAL mode for better concurrent read performance."""
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("Migration 003: Enabled WAL journal mode")


def _migration_004_vector_index(conn: sqlite3.Connection):
    """Add IVF index to fact_embeddings for sub-millisecond search."""
    # Note: sqlite-vec uses a specific syntax for virtual table indexes.
    # In vec0, we can create an index on the embedding column.
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fact_embeddings_ivf "
            "ON fact_embeddings(embedding) USING ivf0"
        )
        logger.info("Migration 004: Added IVF index to fact_embeddings")
    except sqlite3.OperationalError as e:
        # Fallback: if ivf0 is not available in the current sqlite-vec build, 
        # we log it but don't fail, as brute force KNN still works.
        logger.warning("Migration 004 skipped: IVF index not supported by this build (%s)", e)


def _migration_005_fts5_setup(conn: sqlite3.Connection):
    """Setup FTS5 virtual table for high-performance text search."""
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5("
        "    content, project, tags, fact_type,"
        "    content='facts', content_rowid='id'"
        ")"
    )
    # Rebuild FTS index from existing facts
    conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")

    # Triggers to keep FTS5 in sync with facts table
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (new.id, new.content, new.project, new.tags, new.fact_type);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, project, tags, fact_type)
            VALUES ('delete', old.id, old.content, old.project, old.tags, old.fact_type);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, project, tags, fact_type)
            VALUES ('delete', old.id, old.content, old.project, old.tags, old.fact_type);
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (new.id, new.content, new.project, new.tags, new.fact_type);
        END;
    """)
    logger.info("Migration 005: Initialized FTS5 search table with sync triggers")
