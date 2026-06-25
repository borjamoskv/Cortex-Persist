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
_LOG_FMT = "Migration [%03d] %s"


_GRAPH_MEMORY_SCHEMA = """
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
"""


def _migration_006_graph_memory(conn: sqlite3.Connection) -> None:
    """Create tables for Graph Memory (entity-relationship knowledge graph)."""
    conn.executescript(_GRAPH_MEMORY_SCHEMA)
    logger.info(_LOG_FMT, 6, "Created Graph Memory tables (entities + entity_relations)")
