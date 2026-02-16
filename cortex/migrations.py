"""
CORTEX v4.0 — Schema Migrations.

Simple, forward-only migration system using a version table.
Each migration is a function that receives a connection and applies changes.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex")


def ensure_migration_table(conn: sqlite3.Connection):
    """Create the schema_version table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    conn.commit()


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version (0 means fresh DB)."""
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] if row[0] is not None else 0
    except Exception:
        return 0


# ─── Migration Definitions ──────────────────────────────────────────


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


def _migration_007_consensus_layer(conn: sqlite3.Connection):
    """Implement Neural Swarm Consensus (votes + scores)."""
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()
    }
    if "consensus_score" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN consensus_score REAL DEFAULT 1.0")
        logger.info("Migration 007: Added 'consensus_score' column to facts")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS consensus_votes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL REFERENCES facts(id),
            agent   TEXT NOT NULL,
            vote    INTEGER NOT NULL, -- 1 (verify), -1 (dispute)
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(fact_id, agent)
        );
        CREATE INDEX IF NOT EXISTS idx_votes_fact ON consensus_votes(fact_id);
    """)
    logger.info("Migration 007: Created 'consensus_votes' table")


def _migration_008_consensus_refinement(conn: sqlite3.Connection):
    """Refine consensus layer: add index and ensure referential integrity."""
    # Index for preventing Sybil lookups and agent vote history
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_votes_agent ON consensus_votes(agent)"
    )
    logger.info("Migration 008: Added index on consensus_votes(agent)")


def _migration_009_reputation_consensus(conn: sqlite3.Connection):
    """Implement Reputation-Weighted Consensus (RWC) with agents and v2 votes."""
    # 1. Create tables (using scripts from schema.py)
    # Note: These are 'IF NOT EXISTS' so safe to run even if schema.py were applied
    from cortex.schema import (
        CREATE_AGENTS,
        CREATE_VOTES_V2,
        CREATE_TRUST_EDGES,
        CREATE_OUTCOMES,
        CREATE_RWC_INDEXES,
    )

    conn.executescript(CREATE_AGENTS)
    conn.executescript(CREATE_VOTES_V2)
    conn.executescript(CREATE_TRUST_EDGES)
    conn.executescript(CREATE_OUTCOMES)
    conn.executescript(CREATE_RWC_INDEXES)

    # 2. Migrate existing agents from consensus_votes
    # Use hex(randomblob(16)) for a simple unique ID
    conn.execute("""
        INSERT INTO agents (id, public_key, name, agent_type, reputation_score)
        SELECT 
            lower(hex(randomblob(16))),
            '',
            agent,
            'legacy',
            0.5
        FROM (SELECT DISTINCT agent FROM consensus_votes)
        WHERE agent NOT IN (SELECT name FROM agents);
    """)

    # 3. Migrate existing votes to v2
    conn.execute("""
        INSERT INTO consensus_votes_v2 (
            fact_id, agent_id, vote, vote_weight, 
            agent_rep_at_vote, created_at
        )
        SELECT 
            v.fact_id,
            a.id,
            v.vote,
            0.5, -- Initial weight (rep 0.5 * 1.0)
            0.5,
            v.timestamp
        FROM consensus_votes v
        JOIN agents a ON v.agent = a.name
        WHERE NOT EXISTS (
            SELECT 1 FROM consensus_votes_v2 v2 
            WHERE v2.fact_id = v.fact_id AND v2.agent_id = a.id
        );
    """)
    logger.info("Migration 009: Initialized RWC (agents, votes_v2, outcomes)")


# ─── Migration Registry ──────────────────────────────────────────────

MIGRATIONS = [
    (1, "Add updated_at column", _migration_001_add_updated_at),
    (2, "Add performance indexes", _migration_002_add_indexes),
    (3, "Enable WAL mode", _migration_003_enable_wal),
    (4, "Add IVF vector index", _migration_004_vector_index),
    (5, "Setup FTS5 search", _migration_005_fts5_setup),
    (6, "Graph Memory tables", _migration_006_graph_memory),
    (7, "Consensus Layer (votes + score)", _migration_007_consensus_layer),
    (8, "Consensus refinement (index)", _migration_008_consensus_refinement),
    (9, "Reputation-Weighted Consensus", _migration_009_reputation_consensus),
]


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run all pending migrations.

    Args:
        conn: SQLite connection.

    Returns:
        Number of migrations applied.
    """
    from cortex.schema import ALL_SCHEMA

    ensure_migration_table(conn)
    current = get_current_version(conn)
    
    # Apply base schema if database is fresh (version 0)
    if current == 0:
        logger.info("Fresh database detected. Applying base schema...")
        for stmt in ALL_SCHEMA:
            try:
                conn.executescript(stmt)
            except (sqlite3.Error, sqlite3.DatabaseError, RuntimeError) as e:
                if "vec0" in str(stmt) or "no such module" in str(e):
                    logger.warning("Skipping schema statement (likely missing vec0): %s", e)
                else:
                    raise
        conn.commit()
        logger.info("Base schema applied.")
    
    applied = 0

    for version, description, func in MIGRATIONS:
        if version > current:
            logger.info("Applying migration %d: %s", version, description)
            try:
                func(conn)
            except (sqlite3.Error, OSError) as e:
                logger.error(
                    "Migration %d failed: %s. Skipping.", version, e
                )
                conn.rollback()
                continue
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )
            conn.commit()
            applied += 1

    if applied:
        logger.info("Applied %d migration(s). Schema now at version %d",
                     applied, get_current_version(conn))
    return applied
