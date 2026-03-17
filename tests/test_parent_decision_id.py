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
import pytest

from cortex.engine.fact_store_core import insert_fact_record
from cortex.engine.mixins.base import FACT_COLUMNS
from cortex.engine.models import Fact
from cortex.engine.query_mixin import QueryMixin

# ─── Fixtures ────────────────────────────────────────────────────────


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
            source TEXT, meta TEXT DEFAULT '{}',
            consensus_score REAL DEFAULT 1.0,
            hash TEXT, signature TEXT, signer_pubkey TEXT,
            is_quarantined INTEGER DEFAULT 0, quarantined_at TEXT,
            quarantine_reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            tx_id INTEGER, is_tombstoned INTEGER DEFAULT 0,
            tombstoned_at TEXT
        );
        CREATE INDEX idx_facts_parent ON facts(parent_decision_id);
    """)
    yield conn
    await conn.close()


# ─── Phase 1: Data Model & Access Layer ──────────────────────────────


class TestDataModel:
    """Fact dataclass and SQL column mapping."""

    def test_fact_has_parent_decision_id_field(self):
        f = Fact(
            id=1,
            tenant_id="t",
            project="p",
            content="c",
            fact_type="knowledge",
            tags=[],
            confidence="C5",
            valid_from="now",
            valid_until=None,
            source="test",
            meta={},
            created_at="now",
            updated_at="now",
            parent_decision_id=42,
        )
        assert f.parent_decision_id == 42

    def test_to_dict_includes_parent(self):
        f = Fact(
            id=1,
            tenant_id="t",
            project="p",
            content="c",
            fact_type="knowledge",
            tags=[],
            confidence="C5",
            valid_from="now",
            valid_until=None,
            source="test",
            meta={},
            created_at="now",
            updated_at="now",
            parent_decision_id=7,
        )
        d = f.to_dict()
        assert d["parent_decision_id"] == 7

    def test_fact_columns_includes_parent(self):
        assert "parent_decision_id" in FACT_COLUMNS

    def test_insert_fact_record_signature(self):
        sig = inspect.signature(insert_fact_record)
        assert "parent_decision_id" in sig.parameters

    def test_store_mixin_signature(self):
        from cortex.engine.store_mixin import StoreMixin

        sig = inspect.signature(StoreMixin.store)
        assert "parent_decision_id" in sig.parameters


# ─── Phase 2: FK Validation & Auto-Resolve ───────────────────────────


class TestFKValidation:
    """Parent references must exist; invalid ones are cleared."""

    @pytest.mark.asyncio
    async def test_invalid_parent_cleared(self, db):
        fid = await insert_fact_record(
            db,
            "default",
            "proj",
            "test",
            "knowledge",
            [],
            "C5",
            None,
            "test",
            {},
            None,
            parent_decision_id=99999,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (fid,),
        )
        row = await cursor.fetchone()
        assert row[0] is None

    @pytest.mark.asyncio
    async def test_valid_parent_persists(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "parent",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        d2 = await insert_fact_record(
            db,
            "default",
            "proj",
            "child",
            "knowledge",
            [],
            "C5",
            None,
            "test",
            {},
            None,
            parent_decision_id=d1,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (d2,),
        )
        assert (await cursor.fetchone())[0] == d1


class TestAutoResolve:
    """Decisions and errors auto-link to previous decision."""

    @pytest.mark.asyncio
    async def test_first_decision_no_parent(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "first",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (d1,),
        )
        assert (await cursor.fetchone())[0] is None

    @pytest.mark.asyncio
    async def test_second_decision_links_to_first(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "first",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        d2 = await insert_fact_record(
            db,
            "default",
            "proj",
            "second",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (d2,),
        )
        assert (await cursor.fetchone())[0] == d1

    @pytest.mark.asyncio
    async def test_error_links_to_decision(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "decision",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        e1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "error",
            "error",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (e1,),
        )
        assert (await cursor.fetchone())[0] == d1

    @pytest.mark.asyncio
    async def test_knowledge_does_not_auto_resolve(self, db):
        await insert_fact_record(
            db,
            "default",
            "proj",
            "decision",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        k1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "knowledge",
            "knowledge",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (k1,),
        )
        assert (await cursor.fetchone())[0] is None

    @pytest.mark.asyncio
    async def test_explicit_parent_overrides_auto(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "first",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        await insert_fact_record(
            db,
            "default",
            "proj",
            "second",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        # Third decision explicitly points to d1, not d2
        d3 = await insert_fact_record(
            db,
            "default",
            "proj",
            "third",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
            parent_decision_id=d1,
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT parent_decision_id FROM facts WHERE id = ?",
            (d3,),
        )
        assert (await cursor.fetchone())[0] == d1


# ─── Phase 2: Type Reconciliation ────────────────────────────────────


class TestTypeReconciliation:
    """CortexFactModel uses int | None, not str | None."""

    def test_memory_model_type(self):
        import typing

        from cortex.memory.models import CortexFactModel

        field = CortexFactModel.model_fields["parent_decision_id"]
        args = typing.get_args(field.annotation)
        if args:
            assert int in args
            assert str not in args


# ─── Phase 3: Engine API ─────────────────────────────────────────────


class TestEngineAPI:
    """get_causal_chain method existence and signature."""

    def test_get_causal_chain_exists(self):
        assert hasattr(QueryMixin, "get_causal_chain")

    def test_get_causal_chain_signature(self):
        sig = inspect.signature(QueryMixin.get_causal_chain)
        params = sig.parameters
        assert "fact_id" in params
        assert "direction" in params
        assert "max_depth" in params
        assert "tenant_id" in params

    def test_sync_wrapper_exists(self):
        from cortex.engine import CortexEngine

        assert hasattr(CortexEngine, "get_causal_chain_sync")


# ─── Phase 3+4: CLI Integration ──────────────────────────────────────


class TestCLI:
    """CLI commands have correct params."""

    def test_store_has_parent_flag(self):
        from cortex.cli.memory_cmds import store

        params = {p.name for p in store.params}
        assert "parent_id" in params

    def test_trace_chain_exists(self):
        from cortex.cli.memory_cmds import trace_chain

        params = {p.name for p in trace_chain.params}
        assert "fact_id" in params
        assert "direction" in params
        assert "depth" in params


# ─── Phase 5: MCP Integration ────────────────────────────────────────


class TestMCP:
    """MCP tools have parent_decision_id support."""

    def test_cortex_store_has_parent(self):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "cortex",
                "mcp",
                "server.py",
            )
        ) as f:
            src = f.read()
        assert "parent_decision_id: int = 0" in src

    def test_cortex_trace_chain_defined(self):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "cortex",
                "mcp",
                "core_tools.py",
            )
        ) as f:
            src = f.read()
        assert "async def cortex_trace_chain(" in src


# ─── Causal Chain Traversal (CTE) ────────────────────────────────────


class TestCausalChainTraversal:
    """Recursive CTE works for auto-resolved chains."""

    @pytest.mark.asyncio
    async def test_recursive_cte_down(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "root",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        d2 = await insert_fact_record(
            db,
            "default",
            "proj",
            "child",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()

        cursor = await db.execute(
            """
            WITH RECURSIVE chain(id, depth) AS (
                SELECT id, 0 FROM facts WHERE id = ?
                UNION ALL
                SELECT f.id, c.depth + 1
                FROM facts f JOIN chain c
                    ON f.parent_decision_id = c.id
                WHERE c.depth < 10
            )
            SELECT id, depth FROM chain ORDER BY depth
        """,
            (d1,),
        )
        rows = await cursor.fetchall()
        ids = [r[0] for r in rows]
        assert d1 in ids
        assert d2 in ids

    @pytest.mark.asyncio
    async def test_recursive_cte_up(self, db):
        d1 = await insert_fact_record(
            db,
            "default",
            "proj",
            "root",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()
        d2 = await insert_fact_record(
            db,
            "default",
            "proj",
            "child",
            "decision",
            [],
            "C5",
            None,
            "test",
            {},
            None,
        )
        await db.commit()

        cursor = await db.execute(
            """
            WITH RECURSIVE chain(id, depth) AS (
                SELECT id, 0 FROM facts WHERE id = ?
                UNION ALL
                SELECT f.parent_decision_id, c.depth + 1
                FROM facts f JOIN chain c ON f.id = c.id
                WHERE f.parent_decision_id IS NOT NULL
                    AND c.depth < 10
            )
            SELECT id, depth FROM chain ORDER BY depth
        """,
            (d2,),
        )
        rows = await cursor.fetchall()
        ids = [r[0] for r in rows]
        assert d2 in ids
        assert d1 in ids
