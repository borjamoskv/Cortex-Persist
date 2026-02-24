"""
Tests for cortex.compactor — Auto-Compaction Engine.

Covers all strategies: DEDUP, MERGE_ERRORS, STALENESS_PRUNE.
Also tests session compaction, stats, and the complete compact() pipeline.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cortex.compaction.strategies.dedup import find_duplicates
from cortex.compaction.strategies.staleness import find_stale_facts
from cortex.compaction.utils import (
    content_hash as _content_hash,
)
from cortex.compaction.utils import (
    merge_error_contents as _merge_error_contents,
)
from cortex.compaction.utils import (
    normalize_content as _normalize_content,
)
from cortex.compaction.utils import (
    similarity as _similarity,
)
from cortex.compaction.compactor import (
    CompactionResult,
    CompactionStrategy,
    compact,
    compact_session,
    get_compaction_stats,
)
from cortex.engine import CortexEngine

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def engine(tmp_path: Path) -> CortexEngine:
    """Create a CortexEngine with a fresh temp database."""
    db_path = tmp_path / "test_compactor.db"
    eng = CortexEngine(db_path=db_path, auto_embed=False)
    eng.init_db_sync()
    return eng


@pytest.fixture
def seeded_engine(engine: CortexEngine) -> CortexEngine:
    """Engine with pre-loaded facts for compaction testing."""
    # 2 exact duplicates
    engine.store_sync(
        project="test",
        content="The sky is blue - padded to satisfy 20 chars min",
        fact_type="knowledge",
        _skip_dedup=True,
    )
    engine.store_sync(
        project="test",
        content="The sky is blue - padded to satisfy 20 chars min",
        fact_type="knowledge",
        _skip_dedup=True,
    )

    # 2 near-duplicates
    engine.store_sync(
        project="test",
        content="Python is great for scripting",
        fact_type="knowledge",
    )
    engine.store_sync(
        project="test",
        content="Python is great for scripting tasks",
        fact_type="knowledge",
    )

    # 3 identical errors
    engine.store_sync(
        project="test",
        content="Connection timeout to DB",
        fact_type="error",
        _skip_dedup=True,
    )
    engine.store_sync(
        project="test",
        content="Connection timeout to DB",
        fact_type="error",
        _skip_dedup=True,
    )
    engine.store_sync(
        project="test",
        content="Connection timeout to DB",
        fact_type="error",
        _skip_dedup=True,
    )

    # 1 unique fact (should survive compaction)
    engine.store_sync(
        project="test",
        content="CORTEX uses SQLite for storage",
        fact_type="decision",
    )

    # 1 fact in a different project (should not be affected)
    engine.store_sync(
        project="other",
        content="The sky is blue - padded to satisfy 20 chars min",
        fact_type="knowledge",
    )

    return engine


# ─── Helper Tests ────────────────────────────────────────────────────


class TestNormalize:
    def test_basic(self):
        assert _normalize_content("  Hello   World  ") == "hello world"

    def test_case_insensitive(self):
        assert _normalize_content("HELLO") == "hello"

    def test_newlines(self):
        assert _normalize_content("foo\n  bar  \n baz") == "foo bar baz"

    def test_empty(self):
        assert _normalize_content("") == ""


class TestContentHash:
    def test_same_content_same_hash(self):
        assert _content_hash("hello world") == _content_hash("hello world")

    def test_normalized_match(self):
        assert _content_hash("  Hello  WORLD  ") == _content_hash("hello world")

    def test_different_content(self):
        assert _content_hash("hello") != _content_hash("world")


class TestSimilarity:
    def test_identical(self):
        assert _similarity("hello world", "hello world") == 1.0

    def test_similar(self):
        sim = _similarity("hello world", "hello worlds")
        assert sim > 0.8

    def test_different(self):
        sim = _similarity("hello", "completely different text")
        assert sim < 0.3

    def test_case_insensitive(self):
        assert _similarity("HELLO", "hello") == 1.0


class TestMergeErrorContents:
    def test_single_content(self):
        result = _merge_error_contents(["some error"])
        assert result == "some error (occurred 1×)"

    def test_identical_errors(self):
        result = _merge_error_contents(["err", "err", "err"])
        assert "3×" in result

    def test_different_errors(self):
        result = _merge_error_contents(["err1", "err2"])
        assert "Consolidated" in result
        assert "err1" in result
        assert "err2" in result


# ─── CompactionResult Tests ──────────────────────────────────────────


class TestCompactionResult:
    def test_reduction(self):
        r = CompactionResult(project="x", original_count=10, compacted_count=7)
        assert r.reduction == 3

    def test_to_dict(self):
        r = CompactionResult(project="x", original_count=5, compacted_count=3)
        d = r.to_dict()
        assert d["project"] == "x"
        assert d["reduction"] == 2
        assert isinstance(d["deprecated_ids"], list)


# ─── Strategy Tests ──────────────────────────────────────────────────


class TestCompactionStrategy:
    def test_all_strategies(self):
        all_strats = CompactionStrategy.all()
        assert len(all_strats) == 3
        assert CompactionStrategy.DEDUP in all_strats

    def test_string_value(self):
        assert CompactionStrategy.DEDUP.value == "dedup"


# ─── Find Duplicates ────────────────────────────────────────────────


class TestFindDuplicates:
    def test_no_facts(self, engine: CortexEngine):
        assert find_duplicates(engine, "empty_project") == []

    def test_no_duplicates(self, engine: CortexEngine):
        engine.store_sync(
            project="p",
            content="The quantum state of a neutron star collapse",
            fact_type="knowledge",
        )
        engine.store_sync(
            project="p",
            content="Recipe for making sourdough bread from scratch",
            fact_type="knowledge",
        )
        assert find_duplicates(engine, "p") == []

    def test_exact_duplicates(self, engine: CortexEngine):
        engine.store_sync(
            project="p",
            content="duplicate content - padded to satisfy 20 chars min",
            fact_type="knowledge",
            _skip_dedup=True,
        )
        engine.store_sync(
            project="p",
            content="duplicate content - padded to satisfy 20 chars min",
            fact_type="knowledge",
            _skip_dedup=True,
        )
        groups = find_duplicates(engine, "p")
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_near_duplicates(self, engine: CortexEngine):
        engine.store_sync(
            project="p",
            content="This is a long sentence about testing",
            fact_type="knowledge",
        )
        engine.store_sync(
            project="p",
            content="This is a long sentence about testing things",
            fact_type="knowledge",
        )
        groups = find_duplicates(engine, "p", similarity_threshold=0.85)
        assert len(groups) >= 1

    def test_project_isolation(self, engine: CortexEngine):
        engine.store_sync(
            project="a",
            content="same content - padded to satisfy 20 chars min",
            fact_type="knowledge",
        )
        engine.store_sync(
            project="b",
            content="same content - padded to satisfy 20 chars min",
            fact_type="knowledge",
        )
        # Should not find cross-project duplicates
        groups = find_duplicates(engine, "a")
        assert len(groups) == 0


# ─── Find Stale Facts ───────────────────────────────────────────────


class TestFindStaleFacts:
    def test_no_stale(self, engine: CortexEngine):
        engine.store_sync(
            project="p",
            content="fresh fact - padded to satisfy 20 chars min",
            fact_type="knowledge",
        )
        assert find_stale_facts(engine, "p", max_age_days=90) == []

    def test_finds_stale(self, engine: CortexEngine):
        # Insert a fact with old timestamp directly
        conn = engine._get_sync_conn()
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        conn.execute(
            "INSERT INTO facts (project, content, fact_type, valid_from, consensus_score, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("p", "old fact", "knowledge", old_date, 0.3, old_date, old_date),
        )
        conn.commit()

        stale = find_stale_facts(engine, "p", max_age_days=90, min_consensus=0.5)
        assert len(stale) == 1

    def test_high_consensus_not_stale(self, engine: CortexEngine):
        conn = engine._get_sync_conn()
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        conn.execute(
            "INSERT INTO facts (project, content, fact_type, valid_from, consensus_score, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "p",
                "high consensus old",
                "knowledge",
                old_date,
                0.9,
                old_date,
                old_date,
            ),
        )
        conn.commit()

        stale = find_stale_facts(engine, "p", max_age_days=90, min_consensus=0.5)
        assert len(stale) == 0


# ─── Full Compact Pipeline ──────────────────────────────────────────


class TestCompact:
    def test_empty_project(self, engine: CortexEngine):
        result = compact(engine, "nonexistent")
        assert result.reduction == 0
        assert result.details == []

    def test_dry_run(self, seeded_engine: CortexEngine):
        result = compact(seeded_engine, "test", dry_run=True)
        assert result.dry_run is True
        # Dry run should not deprecate anything
        conn = seeded_engine._get_sync_conn()
        active = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE project = 'test' AND valid_until IS NULL"
        ).fetchone()[0]
        assert active == 8  # all originals still active

    def test_dedup_only(self, seeded_engine: CortexEngine):
        result = compact(
            seeded_engine,
            "test",
            strategies=[CompactionStrategy.DEDUP],
        )
        assert "dedup" in result.strategies_applied
        assert result.reduction > 0
        # Canonical facts should survive
        assert result.compacted_count < result.original_count

    def test_merge_errors_only(self, seeded_engine: CortexEngine):
        result = compact(
            seeded_engine,
            "test",
            strategies=[CompactionStrategy.MERGE_ERRORS],
        )
        assert "merge_errors" in result.strategies_applied
        assert len(result.new_fact_ids) >= 1  # consolidated error created

    def test_staleness_prune(self, engine: CortexEngine):
        conn = engine._get_sync_conn()
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        conn.execute(
            "INSERT INTO facts (project, content, fact_type, valid_from, consensus_score, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "p",
                "stale fact",
                "knowledge",
                old_date,
                0.2,
                old_date,
                old_date,
            ),
        )
        conn.commit()

        result = compact(
            engine,
            "p",
            strategies=[CompactionStrategy.STALENESS_PRUNE],
            max_age_days=90,
        )
        assert "staleness_prune" in result.strategies_applied
        assert result.reduction >= 1

    def test_full_pipeline(self, seeded_engine: CortexEngine):
        result = compact(seeded_engine, "test")
        assert result.project == "test"
        assert result.reduction > 0
        assert len(result.strategies_applied) > 0

    def test_project_isolation(self, seeded_engine: CortexEngine):
        compact(seeded_engine, "test")
        # Other project should be unaffected
        conn = seeded_engine._get_sync_conn()
        other_active = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE project = 'other' AND valid_until IS NULL"
        ).fetchone()[0]
        assert other_active == 1

    def test_deprecated_facts_exist(self, seeded_engine: CortexEngine):
        compact(seeded_engine, "test")
        conn = seeded_engine._get_sync_conn()
        deprecated = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE project = 'test' AND valid_until IS NOT NULL"
        ).fetchone()[0]
        assert deprecated > 0


# ─── Session Compaction ──────────────────────────────────────────────


class TestCompactSession:
    def test_empty_project(self, engine: CortexEngine):
        output = compact_session(engine, "empty")
        assert "No active facts" in output

    def test_generates_markdown(self, seeded_engine: CortexEngine):
        output = compact_session(seeded_engine, "test")
        assert "# test" in output
        assert "##" in output

    def test_max_facts_limit(self, engine: CortexEngine):
        for i in range(20):
            engine.store_sync(project="p", content=f"Fact number {i}", fact_type="knowledge")
        output = compact_session(engine, "p", max_facts=5)
        # Should contain markdown but limited content
        assert "# p" in output


# ─── Stats ───────────────────────────────────────────────────────────


class TestGetCompactionStats:
    def test_no_history(self, engine: CortexEngine):
        stats = get_compaction_stats(engine)
        assert stats["total_compactions"] == 0

    def test_after_compaction(self, seeded_engine: CortexEngine):
        compact(seeded_engine, "test")
        stats = get_compaction_stats(seeded_engine)
        assert stats["total_compactions"] >= 1
        assert stats["total_deprecated"] > 0

    def test_project_filter(self, seeded_engine: CortexEngine):
        compact(seeded_engine, "test")
        stats = get_compaction_stats(seeded_engine, project="test")
        assert stats["total_compactions"] >= 1

        stats_other = get_compaction_stats(seeded_engine, project="nonexistent")
        assert stats_other["total_compactions"] == 0
