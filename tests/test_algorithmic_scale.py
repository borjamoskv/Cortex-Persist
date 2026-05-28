"""Tests for algorithmic scaling: indices, FTS5 triggers, WAL checkpoint, pool."""

from __future__ import annotations

import os
import sqlite3

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


# ─── FTS5 Trigger Tests ──────────────────────────────────────────────


class TestFTS5Triggers:
    """Verify facts FTS is application-managed, not trigger-managed."""

    def test_fresh_schema_does_not_install_fact_fts_triggers(self, tmp_path):
        """Fresh DBs must match migrated DBs: no facts_ai/facts_ad/facts_au triggers."""
        from cortex.database.schema import get_all_schema
        from cortex.database.schema_extensions import CREATE_FACTS_FTS_TRIGGERS, EXTENSION_SCHEMA

        assert CREATE_FACTS_FTS_TRIGGERS not in EXTENSION_SCHEMA

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        try:
            for stmt in get_all_schema():
                if "USING vec0" in stmt:
                    continue
                conn.executescript(stmt)
            conn.commit()

            trigger_rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' AND name IN ('facts_ai', 'facts_ad', 'facts_au')"
            ).fetchall()
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(facts_fts)").fetchall()
            }
        finally:
            conn.close()

        assert trigger_rows == []
        assert {"content", "project", "tags", "fact_type", "tenant_id"} <= columns


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
