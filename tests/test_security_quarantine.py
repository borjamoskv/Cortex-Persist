"""
CORTEX v5.2 — Security Quarantine & Ghost Reaper Tests.

Tests for the Cibercentro-inspired security hardening:
1. Migration 018 applies cleanly
2. Quarantine/unquarantine lifecycle
3. Quarantine excludes from recall and dedup
4. Ghost reaper with TTL
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from cortex.database.schema import ALL_SCHEMA
from cortex.migrations.mig_security_hardening import _migration_018_security_hardening


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def fresh_db(tmp_path):
    """Create a fresh SQLite DB with base schema."""
    db_path = tmp_path / "test_quarantine.db"
    conn = sqlite3.connect(str(db_path))
    for stmt in ALL_SCHEMA:
        try:
            conn.executescript(stmt)
        except sqlite3.Error as e:
            if "no such module" in str(e).lower() or "vec0" in str(stmt):
                continue
            raise
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def migrated_db(fresh_db):
    """Apply migration 018 on top of base schema."""
    _migration_018_security_hardening(fresh_db)
    return fresh_db


# ═══════════════════════════════════════════════════════════════════
# Migration Tests
# ═══════════════════════════════════════════════════════════════════


class TestMigration018:
    def test_migration_adds_quarantine_columns(self, migrated_db):
        """Quarantine columns exist in facts table after migration."""
        cursor = migrated_db.execute("PRAGMA table_info(facts)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "is_quarantined" in columns
        assert "quarantined_at" in columns
        assert "quarantine_reason" in columns

    def test_migration_adds_ghost_expires_at(self, migrated_db):
        """expires_at column exists in ghosts table after migration."""
        cursor = migrated_db.execute("PRAGMA table_info(ghosts)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "expires_at" in columns

    def test_migration_idempotent(self, migrated_db):
        """Running migration twice doesn't crash (duplicate column guard)."""
        # Should not raise
        _migration_018_security_hardening(migrated_db)

    def test_quarantine_default_is_zero(self, migrated_db):
        """New facts default to is_quarantined = 0."""
        migrated_db.execute(
            "INSERT INTO facts (project, content, fact_type, valid_from) "
            "VALUES ('test', 'test content here', 'knowledge', datetime('now'))"
        )
        migrated_db.commit()
        cursor = migrated_db.execute(
            "SELECT is_quarantined FROM facts WHERE project = 'test'"
        )
        row = cursor.fetchone()
        assert row[0] == 0


# ═══════════════════════════════════════════════════════════════════
# Quarantine Tests (Engine-level)
# ═══════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def engine(tmp_path):
    """Create a CortexEngine with fresh DB for testing."""
    import os

    os.environ["CORTEX_TESTING"] = "1"
    db_path = str(tmp_path / "test_engine.db")

    from cortex.engine import CortexEngine

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()


@pytest.mark.asyncio
async def test_quarantine_fact(engine):
    """Store → quarantine → fact disappears from recall."""
    fact_id = await engine.store(
        project="test-project",
        content="This fact will be quarantined immediately",
        fact_type="knowledge",
    )

    # Verify it exists in recall
    facts = await engine.recall("test-project")
    assert any(f.id == fact_id for f in facts)

    # Quarantine it
    result = await engine.quarantine(fact_id, "contaminated data — cibercentro audit")
    assert result is True

    # Verify it no longer appears in recall
    facts = await engine.recall("test-project")
    assert not any(f.id == fact_id for f in facts)


@pytest.mark.asyncio
async def test_unquarantine_restores_fact(engine):
    """Quarantine → unquarantine → fact reappears."""
    fact_id = await engine.store(
        project="test-project",
        content="This fact will be quarantined then released",
        fact_type="decision",
    )

    await engine.quarantine(fact_id, "under investigation")
    facts = await engine.recall("test-project")
    assert not any(f.id == fact_id for f in facts)

    result = await engine.unquarantine(fact_id)
    assert result is True

    facts = await engine.recall("test-project")
    assert any(f.id == fact_id for f in facts)


@pytest.mark.asyncio
async def test_quarantine_blocks_dedup(engine):
    """Quarantined fact shouldn't block storing identical content."""
    content = "Unique test content for dedup quarantine check"

    fact_id_1 = await engine.store(
        project="dedup-test",
        content=content,
        fact_type="knowledge",
    )

    # Quarantine original
    await engine.quarantine(fact_id_1, "suspected contamination")

    # Store identical content — should NOT be deduped against quarantined fact
    fact_id_2 = await engine.store(
        project="dedup-test",
        content=content,
        fact_type="knowledge",
    )
    assert fact_id_2 != fact_id_1  # New fact created, not deduped


@pytest.mark.asyncio
async def test_quarantine_requires_reason(engine):
    """Quarantine without reason raises ValueError."""
    fact_id = await engine.store(
        project="test-project",
        content="This fact needs a quarantine reason",
        fact_type="knowledge",
    )
    with pytest.raises(ValueError, match="reason"):
        await engine.quarantine(fact_id, "")


@pytest.mark.asyncio
async def test_quarantine_invalid_fact_id(engine):
    """Quarantine with invalid fact_id raises ValueError."""
    with pytest.raises(ValueError, match="Invalid"):
        await engine.quarantine(-1, "test")


@pytest.mark.asyncio
async def test_unquarantine_nonexistent(engine):
    """Unquarantine on non-quarantined fact returns False."""
    fact_id = await engine.store(
        project="test-project",
        content="This fact was never quarantined at all",
        fact_type="knowledge",
    )
    result = await engine.unquarantine(fact_id)
    assert result is False


# ═══════════════════════════════════════════════════════════════════
# Ghost Reaper Tests
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_ghost_reaper_expires_old_ghosts(tmp_path):
    """Reaper removes ghosts older than TTL."""
    import aiosqlite

    db_path = str(tmp_path / "test_reaper.db")
    async with aiosqlite.connect(db_path) as conn:
        # Create ghosts table with expires_at
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ghosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                reference TEXT NOT NULL,
                context TEXT,
                project TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                target_id INTEGER,
                confidence REAL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at TEXT,
                expires_at TEXT,
                meta TEXT DEFAULT '{}'
            )
        """)

        # Insert an old ghost (60 days ago)
        old_date = (
            datetime.now(timezone.utc) - timedelta(days=60)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        await conn.execute(
            "INSERT INTO ghosts (reference, context, project, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("stale-entity", "old context", "test-project", old_date),
        )

        # Insert a fresh ghost (1 day ago)
        fresh_date = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        await conn.execute(
            "INSERT INTO ghosts (reference, context, project, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("fresh-entity", "new context", "test-project", fresh_date),
        )
        await conn.commit()

        from cortex.engine.reaper import GhostReaper

        reaper = GhostReaper(ttl_days=30)
        reaped = await reaper.reap_db_ghosts(conn)

        assert reaped == 1  # Only the old ghost

        # Verify fresh ghost survives
        cursor = await conn.execute("SELECT COUNT(*) FROM ghosts WHERE status = 'open'")
        count = (await cursor.fetchone())[0]
        assert count == 1


@pytest.mark.asyncio
async def test_ghost_reaper_respects_explicit_ttl(tmp_path):
    """Ghost with explicit expires_at in the future should survive."""
    import aiosqlite

    db_path = str(tmp_path / "test_reaper_explicit.db")
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ghosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                reference TEXT NOT NULL,
                context TEXT,
                project TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                target_id INTEGER,
                confidence REAL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at TEXT,
                expires_at TEXT,
                meta TEXT DEFAULT '{}'
            )
        """)

        # Old ghost but with future expires_at
        old_date = (
            datetime.now(timezone.utc) - timedelta(days=60)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        future_date = (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        await conn.execute(
            "INSERT INTO ghosts (reference, context, project, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("protected-entity", "important", "test", old_date, future_date),
        )
        await conn.commit()

        from cortex.engine.reaper import GhostReaper

        reaper = GhostReaper(ttl_days=30)
        reaped = await reaper.reap_db_ghosts(conn)

        # Ghost has explicit future expires_at — should NOT be reaped
        assert reaped == 0


def test_ghost_reaper_invalid_ttl():
    """Reaper with TTL < 1 raises ValueError."""
    from cortex.engine.reaper import GhostReaper

    with pytest.raises(ValueError, match="ttl_days"):
        GhostReaper(ttl_days=0)


# ═══════════════════════════════════════════════════════════════════
# Bridge Guard Tests
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_bridge_blocked_from_contaminated_project(engine):
    """Bridge from project with high quarantine ratio is blocked."""
    # Store 5 facts in source project
    ids = []
    for i in range(5):
        fid = await engine.store(
            project="contaminated-src",
            content=f"Test fact number {i} for contamination check",
            fact_type="knowledge",
        )
        ids.append(fid)

    # Quarantine 4 of 5 (80% ratio > 15% threshold)
    for fid in ids[:4]:
        await engine.quarantine(fid, "detected contamination")

    # Attempt bridge from contaminated source
    with pytest.raises(ValueError, match="BRIDGE BLOCKED"):
        await engine.store(
            project="clean-dest",
            content="Pattern: X from contaminated-src → clean-dest. Adaptations: Y.",
            fact_type="bridge",
        )


@pytest.mark.asyncio
async def test_bridge_allowed_from_clean_project(engine):
    """Bridge from clean project is allowed."""
    # Store facts in clean source — no quarantines
    await engine.store(
        project="clean-src",
        content="This is a clean fact with no issues at all",
        fact_type="knowledge",
    )

    # Bridge should pass
    bridge_id = await engine.store(
        project="dest-project",
        content="Pattern: Y from clean-src → dest-project. Adaptations: Z.",
        fact_type="bridge",
    )
    assert bridge_id > 0


@pytest.mark.asyncio
async def test_bridge_guard_source_extraction():
    """BridgeGuard correctly extracts source project from content."""
    from cortex.engine.bridge_guard import BridgeGuard

    assert BridgeGuard._extract_source_project(
        "Pattern: X from naroa-web → live-notch", "live-notch"
    ) == "naroa-web"

    assert BridgeGuard._extract_source_project(
        "moskvbot → cortex", "cortex"
    ) == "moskvbot"

    assert BridgeGuard._extract_source_project(
        "No bridge pattern here", "project"
    ) is None
