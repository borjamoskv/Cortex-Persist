import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")


def _migration_022_cognitive_layer(conn: sqlite3.Connection) -> None:
    """Migration 22: Add cognitive_layer and parent_decision_id to facts table."""
    logger.info("Running Migration 22: Stratified Cognition and Causal Anchoring")

    # Check if cognitive_layer already exists
    cursor = conn.execute("PRAGMA table_info(facts)")
    columns = [row[1] for row in cursor.fetchall()]

    if "cognitive_layer" not in columns:
        conn.execute(
            "ALTER TABLE facts ADD COLUMN cognitive_layer TEXT DEFAULT 'semantic' "
            "CHECK( cognitive_layer IN "
            "('working', 'episodic', 'semantic', 'relationship', 'emotional') )"
        )
        logger.info("Added cognitive_layer column to facts table.")

    if "parent_decision_id" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN parent_decision_id INTEGER REFERENCES facts(id)")
        logger.info("Added parent_decision_id column to facts table.")
