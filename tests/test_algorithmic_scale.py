# [C5-REAL] Exergy-Maximized

from __future__ import annotations




import os
import sqlite3

import pytest



# ─── Index Tests ──────────────────────────────────────────────────────


class TestCoveringIndices:
    """Verify new composite indices exist after schema init."""

    def test_tenant_valid_index_exists(self, tmp_path):
        """idx_facts_tenant_valid covers (tenant_id, valid_until)."""
        from cortex.database.schema import CREATE_FACTS, CREATE_FACTS_INDEXES

        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        for stmt in CREATE_FACTS.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        for stmt in CREATE_FACTS_INDEXES.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_facts_tenant_valid'"
        )
        assert cursor.fetchone() is not None, "idx_facts_tenant_valid missing"
        conn.close()

    def test_proj_valid_index_exists(self, tmp_path):
        """idx_facts_proj_valid covers (project, valid_until)."""
        from cortex.database.schema import CREATE_FACTS, CREATE_FACTS_INDEXES

        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        for stmt in CREATE_FACTS.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        for stmt in CREATE_FACTS_INDEXES.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_facts_proj_valid'"
        )
        assert cursor.fetchone() is not None, "idx_facts_proj_valid missing"
        conn.close()


# ─── FTS5 Engine Synchronization Tests ────────────────────────────────


class TestFTS5Triggers:
    """Verify FTS5 manual sync operations via CortexEngine work correctly."""

    @pytest.mark.asyncio
    async def test_insert_trigger_populates_fts(self, tmp_path):
        """Storing via CortexEngine populates facts_fts."""
        from cortex.engine import CortexEngine

        db = str(tmp_path / "test_fts_insert.db")
        engine = CortexEngine(db_path=db, auto_embed=False)
        await engine.init_db()

        await engine.store(
            project="test-proj",
            content="sovereign memory system",
            fact_type="knowledge",
            source="test",
        )

        # Search FTS5
        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT rowid FROM facts_fts WHERE content MATCH 'sovereign'"
            )
            rows = await cursor.fetchall()
            assert len(rows) == 1
        await engine.close()

    @pytest.mark.asyncio
    async def test_update_trigger_syncs_fts(self, tmp_path):
        """Updating via CortexEngine syncs facts_fts."""
        from cortex.engine import CortexEngine

        db = str(tmp_path / "test_fts_update.db")
        engine = CortexEngine(db_path=db, auto_embed=False)
        await engine.init_db()

        fact_id = await engine.store(
            project="test-proj",
            content="old content here",
            fact_type="knowledge",
            source="test",
        )

        await engine.update(
            fact_id=fact_id,
            content="new sovereign content",
        )

        async with engine.session() as conn:
            # Old content should be gone
            cursor = await conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'old'")
            assert await cursor.fetchone() is None

            # New content should be findable
            cursor = await conn.execute(
                "SELECT rowid FROM facts_fts WHERE content MATCH 'sovereign'"
            )
            assert await cursor.fetchone() is not None
        await engine.close()

    @pytest.mark.asyncio
    async def test_delete_trigger_removes_from_fts(self, tmp_path):
        """Purging via CortexEngine removes from facts_fts."""
        from cortex.engine import CortexEngine

        db = str(tmp_path / "test_fts_delete.db")
        engine = CortexEngine(db_path=db, auto_embed=False)
        await engine.init_db()

        fact_id = await engine.store(
            project="test-proj",
            content="ephemeral data",
            fact_type="knowledge",
            source="test",
        )

        await engine.purge(fact_id, force=True)

        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT rowid FROM facts_fts WHERE content MATCH 'ephemeral'"
            )
            assert await cursor.fetchone() is None
        await engine.close()


# ─── WAL Checkpoint Tests ────────────────────────────────────────────


class TestWALCheckpoint:
    """Verify wal_autocheckpoint pragma is set."""

    def test_sync_wal_autocheckpoint(self, tmp_path):
        """Sync connections get wal_autocheckpoint=1000."""
        from cortex.database.core import WAL_AUTOCHECKPOINT, connect

        db = str(tmp_path / "test.db")
        conn = connect(db)
        cursor = conn.execute("PRAGMA wal_autocheckpoint")
        val = cursor.fetchone()[0]
        assert val == WAL_AUTOCHECKPOINT, (
            f"Expected wal_autocheckpoint={WAL_AUTOCHECKPOINT}, got {val}"
        )
        conn.close()

    def test_wal_autocheckpoint_constant(self):
        """WAL_AUTOCHECKPOINT is 1000 pages."""
        from cortex.database.core import WAL_AUTOCHECKPOINT

        assert WAL_AUTOCHECKPOINT == 1000


# ─── Pool Tests ───────────────────────────────────────────────────────


class TestPoolExpansion:
    """Verify pool respects env vars and new defaults."""

    def test_default_pool_min(self):
        """Default min_connections is 4."""
        # Clear env to test defaults
        env = os.environ.copy()
        os.environ.pop("CORTEX_POOL_MIN", None)
        os.environ.pop("CORTEX_POOL_MAX", None)

        try:
            # Re-import to pick up clean env
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(db_path=":memory:")
            assert pool.min_connections == 4, f"Expected min=4, got {pool.min_connections}"
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_default_pool_max(self):
        """Default max_connections is 32."""
        env = os.environ.copy()
        os.environ.pop("CORTEX_POOL_MIN", None)
        os.environ.pop("CORTEX_POOL_MAX", None)

        try:
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(db_path=":memory:")
            assert pool.max_connections == 32, f"Expected max=32, got {pool.max_connections}"
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_env_override_pool_min(self):
        """CORTEX_POOL_MIN overrides default."""
        env = os.environ.copy()
        os.environ["CORTEX_POOL_MIN"] = "8"

        try:
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(db_path=":memory:")
            assert pool.min_connections == 8, f"Expected min=8, got {pool.min_connections}"
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_env_override_pool_max(self):
        """CORTEX_POOL_MAX overrides default."""
        env = os.environ.copy()
        os.environ["CORTEX_POOL_MAX"] = "64"

        try:
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(db_path=":memory:")
            assert pool.max_connections == 64, f"Expected max=64, got {pool.max_connections}"
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_explicit_args_override_env(self):
        """Explicit constructor args override env vars."""
        env = os.environ.copy()
        os.environ["CORTEX_POOL_MIN"] = "8"
        os.environ["CORTEX_POOL_MAX"] = "64"

        try:
            from cortex.database.pool import CortexConnectionPool

            pool = CortexConnectionPool(
                db_path=":memory:",
                min_connections=3,
                max_connections=15,
            )
            assert pool.min_connections == 3
            assert pool.max_connections == 15
        finally:
            os.environ.clear()
            os.environ.update(env)
