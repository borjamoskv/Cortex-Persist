"""Tests for Memory Governance — reaper (DB ghosts) and confidence decay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from cortex.engine.confidence_decay import ConfidenceDecay
from cortex.engine.reaper import GhostReaper

# ── Ghost Reaper Tests (DB ghosts only) ───────────────────────────


@pytest.fixture
async def reaper_db(tmp_path):
    """Create a minimal DB with ghosts table for reaper tests."""
    db_path = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE ghosts (
                id INTEGER PRIMARY KEY,
                project TEXT,
                content TEXT,
                created_at TEXT,
                ttl_days INTEGER DEFAULT 30,
                status TEXT DEFAULT 'open',
                expires_at TEXT,
                resolved_at TEXT
            )
        """)
        await conn.commit()
        yield conn


class TestGhostReaper:
    """Test reap_db_ghosts removes expired ghost entries."""

    async def test_reap_expired_ghost(self, reaper_db):
        past = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        await reaper_db.execute(
            "INSERT INTO ghosts (project, content, created_at, ttl_days) "
            "VALUES (?, ?, ?, ?)",
            ("test", "stale ghost content here", past, 30),
        )
        await reaper_db.commit()

        reaper = GhostReaper(ttl_days=30)
        reaped = await reaper.reap_db_ghosts(reaper_db)
        assert reaped >= 1

    async def test_skip_fresh_ghost(self, reaper_db):
        recent = datetime.now(timezone.utc).isoformat()
        await reaper_db.execute(
            "INSERT INTO ghosts (project, content, created_at, ttl_days) "
            "VALUES (?, ?, ?, ?)",
            ("test", "fresh ghost content here", recent, 30),
        )
        await reaper_db.commit()

        reaper = GhostReaper(ttl_days=30)
        reaped = await reaper.reap_db_ghosts(reaper_db)
        assert reaped == 0

    async def test_skip_resolved_ghost(self, reaper_db):
        past = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        await reaper_db.execute(
            "INSERT INTO ghosts (project, content, created_at, ttl_days, status) "
            "VALUES (?, ?, ?, ?, ?)",
            ("test", "resolved ghost content", past, 30, "resolved"),
        )
        await reaper_db.commit()

        reaper = GhostReaper(ttl_days=30)
        reaped = await reaper.reap_db_ghosts(reaper_db)
        assert reaped == 0


# ── Confidence Decay Tests ─────────────────────────────────────────


@pytest.fixture
async def decay_db(tmp_path):
    """Create a minimal DB with facts table for decay tests."""
    db_path = str(tmp_path / "decay.db")
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT,
                content TEXT,
                fact_type TEXT DEFAULT 'knowledge',
                confidence TEXT DEFAULT 'stated',
                valid_from TEXT,
                valid_until TEXT,
                updated_at TEXT,
                is_quarantined INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                created_at TEXT
            )
        """)
        await conn.commit()
        yield conn


class TestConfidenceDecay:
    """Test confidence degradation over time."""

    async def test_stated_decays_to_c3_after_14_days(self, decay_db):
        old = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        await decay_db.execute(
            "INSERT INTO facts (project, content, fact_type, confidence, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("test", "old stated content 12345", "knowledge", "stated", old),
        )
        await decay_db.commit()

        engine = ConfidenceDecay()
        result = await engine.decay(decay_db)
        assert result["downgraded"] >= 1

        cursor = await decay_db.execute("SELECT confidence FROM facts WHERE id = 1")
        row = await cursor.fetchone()
        assert row[0] == "C3"

    async def test_exempt_types_not_decayed(self, decay_db):
        old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        for ft in ("identity", "axiom", "rule", "schema", "preference"):
            await decay_db.execute(
                "INSERT INTO facts (project, content, fact_type, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test", f"permanent {ft} content here", ft, "stated", old),
            )
        await decay_db.commit()

        engine = ConfidenceDecay()
        result = await engine.decay(decay_db)
        assert result["downgraded"] == 0
        assert result["deprecated"] == 0

    async def test_recently_accessed_not_decayed(self, decay_db):
        old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        recent = datetime.now(timezone.utc).isoformat()
        await decay_db.execute(
            "INSERT INTO facts (project, content, fact_type, confidence, "
            "created_at, last_accessed_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("test", "recently accessed content", "knowledge", "stated", old, recent),
        )
        await decay_db.commit()

        engine = ConfidenceDecay()
        result = await engine.decay(decay_db)
        assert result["downgraded"] == 0

    async def test_c2_deprecated_after_60_days(self, decay_db):
        old = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
        await decay_db.execute(
            "INSERT INTO facts (project, content, fact_type, confidence, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("test", "very old C2 content here", "knowledge", "C2", old),
        )
        await decay_db.commit()

        engine = ConfidenceDecay()
        result = await engine.decay(decay_db)
        assert result["deprecated"] >= 1

        cursor = await decay_db.execute("SELECT valid_until FROM facts WHERE id = 1")
        row = await cursor.fetchone()
        assert row[0] is not None
