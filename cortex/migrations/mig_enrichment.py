"""Migration 024: P0 Decoupling - Enrichment Queue."""

import sqlite3


def _migration_024_enrichment_queue(conn: sqlite3.Connection):
    """Add semantic_status to facts and create enrichment_jobs table."""
    # 1. Add semantic_status and semantic_error to facts
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN semantic_status TEXT NOT NULL DEFAULT 'pending'")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

    try:
        conn.execute("ALTER TABLE facts ADD COLUMN semantic_error TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

    # 2. Update existing facts to 'completed' assuming anything existing has been embedded
    # if the system was functioning normally before. If not, they might be lacking embeddings,
    # but the old system didn't track "pending" state explicitly.
    conn.execute("UPDATE facts SET semantic_status = 'completed' WHERE semantic_status = 'pending'")

    # 3. Create enrichment_jobs table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS enrichment_jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id       TEXT NOT NULL DEFAULT 'default',
            fact_id         INTEGER NOT NULL REFERENCES facts(id),
            job_type        TEXT NOT NULL DEFAULT 'embedding',
            status          TEXT NOT NULL DEFAULT 'queued',
            priority        INTEGER DEFAULT 0,
            attempts        INTEGER DEFAULT 0,
            last_error      TEXT,
            payload         TEXT,
            next_attempt_at TEXT,
            locked_at       TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_enrichment_status ON enrichment_jobs(status, locked_at);"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_enrichment_fact ON enrichment_jobs(fact_id);")
