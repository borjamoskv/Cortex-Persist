import logging

from aiosqlite import Connection

logger = logging.getLogger("cortex.migrations")


async def _migration_022_cognitive_layer(conn: Connection) -> None:
    """Migration 22: Add cognitive_layer and parent_decision_id to facts table."""
    logger.info("Running Migration 22: Stratified Cognition and Causal Anchoring")

    # Check if cognitive_layer already exists
    cursor = await conn.execute("PRAGMA table_info(facts)")
    columns = [row[1] for row in await cursor.fetchall()]

    if "cognitive_layer" not in columns:
        await conn.execute(
            "ALTER TABLE facts ADD COLUMN cognitive_layer TEXT DEFAULT 'semantic' "
            "CHECK( cognitive_layer IN "
            "('working', 'episodic', 'semantic', 'relationship', 'emotional') )"
        )
        logger.info("Added cognitive_layer column to facts table.")

    if "parent_decision_id" not in columns:
        await conn.execute(
            "ALTER TABLE facts ADD COLUMN parent_decision_id INTEGER REFERENCES facts(id)"
        )
        logger.info("Added parent_decision_id column to facts table.")
