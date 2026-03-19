"""Tests for algorithmic scaling: indices, FTS5 triggers, WAL checkpoint, pool."""

from __future__ import annotations

import os
import sqlite3

# ─── Index Tests ──────────────────────────────────────────────────────


class TestCoveringIndices:
    """Verify new composite indices exist after schema init."""

    def test_tenant_valid_index_exists(self, tmp_path):
        """idx_facts_tenant_valid covers (tenant_id, valid_until)."""
        from cortex.database.schema import CREATE_FACTS_INDEXES, CREATE_FACTS_TABLE

        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        for stmt in CREATE_FACTS_TABLE.strip().split(";"):
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
        from cortex.database.schema import CREATE_FACTS_INDEXES, CREATE_FACTS_TABLE

        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        for stmt in CREATE_FACTS_TABLE.strip().split(";"):
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


# ─── FTS5 Trigger Tests ──────────────────────────────────────────────


class TestFTS5Triggers:
    """Verify FTS5 auto-sync triggers fire correctly."""

    def _setup_db(self, db_path: str) -> sqlite3.Connection:
        """Create facts table + FTS5 + triggers."""
        from cortex.database.schema import CREATE_FACTS_INDEXES
        from cortex.database.schema_extensions import (
            CREATE_FACTS_FTS,
            CREATE_FACTS_FTS_TRIGGERS,
        )

        conn = sqlite3.connect(db_path)
        for stmt in CREATE_FACTS_TABLE.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        for stmt in CREATE_FACTS_INDEXES.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        # FTS5 virtual table
        conn.executescript(CREATE_FACTS_FTS)
        # Triggers
        conn.executescript(CREATE_FACTS_FTS_TRIGGERS)
        conn.commit()
        return conn

    def test_insert_trigger_populates_fts(self, tmp_path):
        """INSERT into facts auto-populates facts_fts."""
        conn = self._setup_db(str(tmp_path / "test.db"))
        conn.execute(
            "INSERT INTO facts "
            "(tenant_id, project, content, fact_type, confidence, "
            "valid_from, tags, source, meta, consensus_score, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "default",
                "test-proj",
                "sovereign memory system",
                "decision",
                "C4",
                "2026-01-01",
                "[]",
                "test",
                "{}",
                1.0,
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        # Search FTS5
        cursor = conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'sovereign'")
        rows = cursor.fetchall()
        assert len(rows) == 1, f"Expected 1 FTS hit, got {len(rows)}"
        conn.close()

    def test_update_trigger_syncs_fts(self, tmp_path):
        """UPDATE facts.content syncs to facts_fts."""
        conn = self._setup_db(str(tmp_path / "test.db"))
        conn.execute(
            "INSERT INTO facts "
            "(tenant_id, project, content, fact_type, confidence, "
            "valid_from, tags, source, meta, consensus_score, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "default",
                "test-proj",
                "old content here",
                "decision",
                "C4",
                "2026-01-01",
                "[]",
                "test",
                "{}",
                1.0,
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        conn.execute("UPDATE facts SET content = 'new sovereign content' WHERE id = 1")
        conn.commit()

        # Old content should be gone
        cursor = conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'old'")
        assert cursor.fetchone() is None, "Old content still in FTS"

        # New content should be findable
        cursor = conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'sovereign'")
        assert cursor.fetchone() is not None, "New content missing from FTS"
        conn.close()

    def test_delete_trigger_removes_from_fts(self, tmp_path):
        """DELETE from facts removes from facts_fts."""
        conn = self._setup_db(str(tmp_path / "test.db"))
        conn.execute(
            "INSERT INTO facts "
            "(tenant_id, project, content, fact_type, confidence, "
            "valid_from, tags, source, meta, consensus_score, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "default",
                "test-proj",
                "ephemeral data",
                "decision",
                "C4",
                "2026-01-01",
                "[]",
                "test",
                "{}",
                1.0,
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        conn.execute("DELETE FROM facts WHERE id = 1")
        conn.commit()

        cursor = conn.execute("SELECT rowid FROM facts_fts WHERE content MATCH 'ephemeral'")
        assert cursor.fetchone() is None, "Deleted fact still in FTS"
        conn.close()


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
            from cortex.database.pool import AsyncConnectionPool

            pool = AsyncConnectionPool(db_path=":memory:")
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
            from cortex.database.pool import AsyncConnectionPool

            pool = AsyncConnectionPool(db_path=":memory:")
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

            pool = CortexConnectionPool(":memory:")
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

            pool = CortexConnectionPool(":memory:")
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
            from cortex.database.pool import AsyncConnectionPool

            pool = AsyncConnectionPool(
                db_path=":memory:",
                min_connections=3,
                max_connections=15,
            )
            assert pool.min_connections == 3
            assert pool.max_connections == 15
        finally:
            os.environ.clear()
            os.environ.update(env)
