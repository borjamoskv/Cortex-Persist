# [C5-REAL] Exergy-Maximized
import pytest
import aiosqlite


@pytest.fixture
async def db(monkeypatch):
    """In-memory SQLite with facts table."""
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT DEFAULT 'default', project TEXT, action TEXT,
            detail TEXT, prev_hash TEXT, hash TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT DEFAULT 'default', project TEXT NOT NULL,
            content TEXT NOT NULL, fact_type TEXT DEFAULT 'knowledge',
            tags TEXT DEFAULT '[]', cognitive_layer TEXT DEFAULT 'semantic',
            parent_decision_id INTEGER REFERENCES facts(id),
            confidence TEXT DEFAULT 'stated',
            valid_from TEXT DEFAULT (datetime('now')), valid_until TEXT,
            source TEXT, metadata TEXT DEFAULT '{}', meta TEXT DEFAULT '{}',
            confidence_rank INTEGER DEFAULT 3, parent_id INTEGER,
            relation_type TEXT, quadrant TEXT DEFAULT 'ACTIVE',
            storage_tier TEXT DEFAULT 'HOT', exergy_score REAL DEFAULT 1.0,
            category TEXT DEFAULT 'general', yield_score REAL DEFAULT 1.0,
            semantic_status TEXT DEFAULT 'pending',
            consensus_score REAL DEFAULT 1.0,
            hash TEXT, signature TEXT, signer_pubkey TEXT,
            is_quarantined INTEGER DEFAULT 0, quarantined_at TEXT,
            quarantine_reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            tx_id INTEGER, is_tombstoned INTEGER DEFAULT 0,
            tombstoned_at TEXT
        );
        CREATE TRIGGER facts_parent_decision_ai
        AFTER INSERT ON facts
        WHEN NEW.parent_id IS NOT NULL
        BEGIN
            UPDATE facts
            SET parent_decision_id = NEW.parent_id
            WHERE id = NEW.id;
        END;
        CREATE TRIGGER facts_parent_decision_au
        AFTER UPDATE OF parent_id ON facts
        WHEN NEW.parent_id IS NOT NULL
        BEGIN
            UPDATE facts
            SET parent_decision_id = NEW.parent_id
            WHERE id = NEW.id;
        END;
        CREATE INDEX idx_facts_parent ON facts(parent_decision_id);
    """)
    yield conn
    await conn.close()
