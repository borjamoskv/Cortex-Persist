# [C5-REAL] Exergy-Maximized
import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)


def _migration_028_dual_identity(conn: sqlite3.Connection) -> None:
    """
    Implements the Dual Identity Paradigm (DIP) to resolve ATMS/sqlite-vec clash.
    Adds `fact_hash` TEXT UNIQUE to facts and causal_edges.
    Populates existing rows with cryptographic UUIDs.
    """
    logger.info("Executing Migration 028: Dual Identity Paradigm (DIP) Injection")

    # 1. Add columns (nullable to bypass SQLite ALTER constraints)
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN fact_hash TEXT;")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_hash ON facts(fact_hash);")
        logger.info("Added fact_hash column to facts.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise

    try:
        conn.execute("ALTER TABLE causal_edges ADD COLUMN fact_hash TEXT;")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_causal_edges_hash ON causal_edges(fact_hash);"
        )
        logger.info("Added fact_hash column to causal_edges.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise

    # 2. Populate UUIDs for facts
    facts_cursor = conn.execute("SELECT id FROM facts WHERE fact_hash IS NULL")
    fact_ids = [row[0] for row in facts_cursor.fetchall()]

    for fid in fact_ids:
        new_uuid = str(uuid.uuid4())
        conn.execute("UPDATE facts SET fact_hash = ? WHERE id = ?", (new_uuid, fid))

    if fact_ids:
        logger.info(f"Generated {len(fact_ids)} DIP hashes for existing facts.")

    # 3. Populate UUIDs for causal_edges
    edges_cursor = conn.execute("SELECT id FROM causal_edges WHERE fact_hash IS NULL")
    edge_ids = [row[0] for row in edges_cursor.fetchall()]

    for eid in edge_ids:
        new_uuid = str(uuid.uuid4())
        conn.execute("UPDATE causal_edges SET fact_hash = ? WHERE id = ?", (new_uuid, eid))

    if edge_ids:
        logger.info(f"Generated {len(edge_ids)} DIP hashes for existing causal_edges.")
