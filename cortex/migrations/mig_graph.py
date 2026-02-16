import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_006_graph_memory(conn: sqlite3.Connection):
    """Create tables for Graph Memory (entity-relationship knowledge graph)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT 'unknown',
            project TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            mention_count INTEGER DEFAULT 1,
            meta TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_entities_name_project
            ON entities(name, project);
        CREATE INDEX IF NOT EXISTS idx_entities_type
            ON entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_entities_project
            ON entities(project);

        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id),
            target_entity_id INTEGER NOT NULL REFERENCES entities(id),
            relation_type TEXT NOT NULL DEFAULT 'related_to',
            weight REAL DEFAULT 1.0,
            first_seen TEXT NOT NULL,
            source_fact_id INTEGER REFERENCES facts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_relations_source
            ON entity_relations(source_entity_id);
        CREATE INDEX IF NOT EXISTS idx_relations_target
            ON entity_relations(target_entity_id);
    """)
    logger.info("Migration 006: Created Graph Memory tables (entities + entity_relations)")
