"""
CORTEX v4.0 — Episodic Memory Tests.

Tests for episode CRUD, pattern detection, boot payload generation,
FTS search, and edge cases.
"""

import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.episodic.main import (
    Episode,
    EpisodicMemory,
    _extract_tokens,
)

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    """Create a temporary CORTEX engine."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)
    for ext in ["-wal", "-shm"]:
        if os.path.exists(db_path + ext):
            os.unlink(db_path + ext)


@pytest.fixture
async def memory(engine):
    """Create an EpisodicMemory instance with a live connection."""
    conn = await engine.get_conn()
    return EpisodicMemory(conn)


@pytest.fixture
async def populated_memory(memory):
    """Memory with pre-loaded multi-session episodes."""
    # Session A: cortex project
    await memory.record("session-a", "decision", "Migrated from JSON to SQLite storage", "cortex")
    await memory.record(
        "session-a", "error", "SQLite locking issue with concurrent writes", "cortex"
    )
    await memory.record("session-a", "discovery", "FTS5 supports content sync tables", "cortex")

    # Session B: cortex project (same themes)
    await memory.record(
        "session-b", "decision", "Adopted SQLite-vec for vector embeddings", "cortex"
    )
    await memory.record(
        "session-b", "error", "SQLite connection pool exhaustion under load", "cortex"
    )

    # Session C: naroa project
    await memory.record("session-c", "decision", "Switched to Vite build system for naroa", "naroa")
    await memory.record("session-c", "milestone", "LCP optimized to under 3 seconds", "naroa")

    # Session D: cortex project
    await memory.record(
        "session-d", "insight", "SQLite WAL mode improves concurrent reads", "cortex"
    )
    await memory.record(
        "session-d", "flow_state", "Deep work on episodic memory engine", "cortex", "flow"
    )

    return memory


# ─── Episode CRUD Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestEpisodeCRUD:
    async def test_record_returns_id(self, memory):
        ep_id = await memory.record(
            "test-session",
            "decision",
            "Test decision content",
            "test-project",
        )
        assert isinstance(ep_id, int)
        assert ep_id > 0

    async def test_recall_returns_episodes(self, memory):
        await memory.record("s1", "decision", "First decision", "proj")
        await memory.record("s1", "error", "First error encountered", "proj")

        episodes = await memory.recall(project="proj")
        assert len(episodes) == 2
        assert all(isinstance(e, Episode) for e in episodes)

    async def test_recall_filter_by_type(self, populated_memory):
        errors = await populated_memory.recall(event_type="error")
        assert len(errors) == 2
        assert all(e.event_type == "error" for e in errors)

    async def test_recall_filter_by_project(self, populated_memory):
        naroa = await populated_memory.recall(project="naroa")
        assert len(naroa) == 2
        assert all(e.project == "naroa" for e in naroa)

    async def test_recall_ordered_by_recency(self, populated_memory):
        episodes = await populated_memory.recall()
        timestamps = [e.created_at for e in episodes]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_recall_with_limit(self, populated_memory):
        episodes = await populated_memory.recall(limit=3)
        assert len(episodes) == 3

    async def test_invalid_event_type_fallback(self, memory):
        await memory.record("s1", "nonexistent_type", "Content", "proj")
        episodes = await memory.recall()
        assert episodes[0].event_type == "insight"  # fallback

    async def test_invalid_emotion_fallback(self, memory):
        await memory.record(
            "s1",
            "decision",
            "Content",
            "proj",
            emotion="rage",
        )
        episodes = await memory.recall()
        assert episodes[0].emotion == "neutral"  # fallback

    async def test_episode_to_dict(self, memory):
        await memory.record(
            "s1",
            "decision",
            "Important choice",
            "proj",
            tags=["architecture", "db"],
            meta={"impact": "high"},
        )
        episodes = await memory.recall()
        d = episodes[0].to_dict()
        assert d["session_id"] == "s1"
        assert d["event_type"] == "decision"
        assert "architecture" in d["tags"]
        assert d["meta"]["impact"] == "high"

    async def test_count(self, populated_memory):
        total = await populated_memory.count()
        assert total == 9

        cortex_count = await populated_memory.count(project="cortex")
        assert cortex_count == 7

    async def test_session_timeline(self, populated_memory):
        timeline = await populated_memory.get_session_timeline("session-a")
        assert len(timeline) == 3
        # Chronological order
        timestamps = [e.created_at for e in timeline]
        assert timestamps == sorted(timestamps)


# ─── FTS Search Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFTSSearch:
    async def test_fts_search_finds_results(self, populated_memory):
        results = await populated_memory.recall(search="SQLite")
        assert len(results) >= 3

    async def test_fts_search_with_project_filter(self, populated_memory):
        results = await populated_memory.recall(search="SQLite", project="cortex")
        assert len(results) >= 3
        assert all(r.project == "cortex" for r in results)

    async def test_fts_search_no_results(self, populated_memory):
        results = await populated_memory.recall(search="quantum_entanglement_xyz")
        assert len(results) == 0


# ─── Pattern Detection Tests ────────────────────────────────────────


@pytest.mark.asyncio
class TestPatternDetection:
    async def test_detect_patterns_finds_recurring(self, populated_memory):
        patterns = await populated_memory.detect_patterns(
            project="cortex",
            min_occurrences=2,
        )
        assert len(patterns) > 0

        # "sqlite" should be detected as recurring across sessions
        themes = [p.theme for p in patterns]
        assert "sqlite" in themes

    async def test_patterns_contain_session_info(self, populated_memory):
        patterns = await populated_memory.detect_patterns(
            project="cortex",
            min_occurrences=2,
        )
        sqlite_pattern = next(
            (p for p in patterns if p.theme == "sqlite"),
            None,
        )
        assert sqlite_pattern is not None
        assert sqlite_pattern.occurrences >= 2
        assert len(sqlite_pattern.sessions) >= 2

    async def test_patterns_empty_when_no_data(self, memory):
        patterns = await memory.detect_patterns()
        assert patterns == []

    async def test_patterns_respect_min_occurrences(self, populated_memory):
        high_min = await populated_memory.detect_patterns(min_occurrences=10)
        assert high_min == []

    async def test_pattern_to_dict(self, populated_memory):
        patterns = await populated_memory.detect_patterns(
            project="cortex",
            min_occurrences=2,
        )
        if patterns:
            d = patterns[0].to_dict()
            assert "theme" in d
            assert "occurrences" in d
            assert "sessions" in d
            assert "event_types" in d


# ─── Token Extraction Tests ─────────────────────────────────────────


@pytest.mark.asyncio
class TestTokenExtraction:
    async def test_extract_tokens_basic(self):
        tokens = _extract_tokens("Migrated from JSON to SQLite storage")
        assert "sqlite" in tokens
        assert "migrated" in tokens
        assert "json" in tokens  # 4 chars, passes filter
        assert "from" not in tokens  # stop word

    async def test_extract_tokens_ignores_short(self):
        tokens = _extract_tokens("a b cd xyz")
        assert len(tokens) == 0  # all < 4 chars

    async def test_extract_tokens_deduplicates(self):
        tokens = _extract_tokens("SQLite sqlite SQLITE")
        assert tokens == {"sqlite"}


# ─── Boot Payload Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestBootPayload:
    async def test_generate_boot_empty_db(self, engine):
        from cortex.episodic.boot import generate_session_boot

        conn = await engine.get_conn()
        payload = await generate_session_boot(conn)

        assert payload.timestamp
        assert payload.total_episodes == 0
        assert payload.episodes == []
        assert payload.patterns == []

    async def test_generate_boot_with_data(self, engine, populated_memory):
        from cortex.episodic.boot import generate_session_boot

        conn = await engine.get_conn()
        payload = await generate_session_boot(conn, project_hint="cortex")

        assert payload.total_episodes > 0
        assert len(payload.episodes) > 0

    async def test_boot_to_markdown(self, engine, populated_memory):
        from cortex.episodic.boot import generate_session_boot

        conn = await engine.get_conn()
        payload = await generate_session_boot(conn, project_hint="cortex")
        md = payload.to_markdown()

        assert "Session Boot" in md
        assert "cortex" in md.lower()
        assert "Recent Memory" in md

    async def test_boot_to_dict(self, engine, populated_memory):
        from cortex.episodic.boot import generate_session_boot

        conn = await engine.get_conn()
        payload = await generate_session_boot(conn, project_hint="cortex")
        d = payload.to_dict()

        assert "timestamp" in d
        assert "episodes" in d
        assert "patterns" in d
        assert "total_episodes" in d
        assert isinstance(d["episodes"], list)


# ─── Edge Cases ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEdgeCases:
    async def test_empty_content_stored(self, memory):
        # Should still store (empty is valid for some event types)
        ep_id = await memory.record("s1", "flow_state", "   ", "proj")
        assert ep_id > 0

    async def test_very_long_content(self, memory):
        long_content = "A" * 10_000
        await memory.record("s1", "insight", long_content, "proj")
        episodes = await memory.recall()
        assert len(episodes[0].content) == 10_000

    async def test_special_characters_in_content(self, memory):
        content = "Decisión: usar 'FTS5' para búsqueda — ¡funciona! 🎉"
        await memory.record("s1", "decision", content, "proj")
        episodes = await memory.recall()
        assert episodes[0].content == content

    async def test_null_project(self, memory):
        await memory.record("s1", "insight", "General insight", None)
        episodes = await memory.recall()
        assert episodes[0].project is None

    async def test_concurrent_sessions(self, memory):
        await memory.record("s1", "decision", "Session 1 decision", "proj")
        await memory.record("s2", "decision", "Session 2 decision", "proj")
        await memory.record("s1", "error", "Session 1 error", "proj")

        timeline_s1 = await memory.get_session_timeline("s1")
        assert len(timeline_s1) == 2

        timeline_s2 = await memory.get_session_timeline("s2")
        assert len(timeline_s2) == 1
