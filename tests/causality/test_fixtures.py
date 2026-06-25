# [C5-REAL] Exergy-Maximized
"""Permanent pytest tests for parent_decision_id causal infrastructure.

Covers:
- Phase 1: Data model, SQL roundtrip, schema index
- Phase 2: Type reconciliation, FK validation, auto-resolve (decision)
- Phase 3: Auto-resolve (error), get_causal_chain API, CLI integration
- Phase 5: MCP tool params, sync wrappers
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault(
    "CORTEX_MASTER_KEY",
    base64.b64encode(os.urandom(32)).decode(),
)

import inspect

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
import pytest

from babylon60.engine.fact_store_core import insert_fact_record
from babylon60.engine.mixins.base import FACT_COLUMNS
from babylon60.engine.models import Fact
from babylon60.engine.query_mixin import QueryMixin


@pytest.fixture
async def db():
    """In-memory SQLite with facts table."""
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
