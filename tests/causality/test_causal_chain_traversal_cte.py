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
