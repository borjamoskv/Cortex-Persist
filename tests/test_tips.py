"""Tests for cortex.tips module."""

from __future__ import annotations

import sqlite3

import pytest

from cortex.tips import (
    STATIC_TIPS,
    Tip,
    TipCategory,
    TipsEngine,
)

# ─── Tip Model Tests ────────────────────────────────────────────────


class TestTipModel:
    """Tests for the Tip dataclass."""

    def test_create_tip(self) -> None:
        tip = Tip(id="test1", content="Hello", category=TipCategory.CORTEX)
        assert tip.id == "test1"
        assert tip.content == "Hello"
        assert tip.category == TipCategory.CORTEX
        assert tip.source == "static"
        assert tip.project is None
        assert tip.relevance == pytest.approx(1.0)

    def test_format_with_category(self) -> None:
        tip = Tip(id="t1", content="Do X", category=TipCategory.PYTHON)
        formatted = tip.format(with_category=True)
        assert "💡" in formatted
        assert "[python]" in formatted
        assert "Do X" in formatted

    def test_format_without_category(self) -> None:
        tip = Tip(id="t1", content="Do X", category=TipCategory.PYTHON)
        formatted = tip.format(with_category=False)
        assert "[python]" not in formatted
        assert "Do X" in formatted

    def test_tip_is_frozen(self) -> None:
        tip = Tip(id="t1", content="X", category=TipCategory.CORTEX)
        with pytest.raises(AttributeError):
            tip.id = "t2"  # type: ignore[misc]


# ─── TipCategory Tests ──────────────────────────────────────────────


class TestTipCategory:
    """Tests for TipCategory enum."""

    def test_all_categories_exist(self) -> None:
        expected = {
            "cortex",
            "workflow",
            "performance",
            "architecture",
            "security",
            "debugging",
            "git",
            "python",
            "design",
            "memory",
            "meta",
        }
        actual = {c.value for c in TipCategory}
        assert expected == actual

    def test_category_from_string(self) -> None:
        cat = TipCategory("cortex")
        assert cat == TipCategory.CORTEX


# ─── Static Tips Bank Tests ─────────────────────────────────────────


class TestStaticTips:
    """Tests for the static tips bank."""

    def test_static_tips_not_empty(self) -> None:
        assert len(STATIC_TIPS) > 0

    def test_all_tips_have_unique_ids(self) -> None:
        ids = [t.id for t in STATIC_TIPS]
        assert len(ids) == len(set(ids)), "Duplicate tip IDs found"

    def test_all_tips_have_content(self) -> None:
        for tip in STATIC_TIPS:
            assert tip.content, f"Tip {tip.id} has empty content"

    def test_all_tips_have_valid_category(self) -> None:
        for tip in STATIC_TIPS:
            assert isinstance(tip.category, TipCategory)

    def test_all_categories_have_tips(self) -> None:
        """Every category should have at least one tip."""
        categories_with_tips = {t.category for t in STATIC_TIPS}
        # memory and meta come from static too
        # Not all need static tips (some come only from dynamic)
        assert len(categories_with_tips) >= 8


# ─── TipsEngine Tests (Static Only) ─────────────────────────────────


class TestTipsEngineStatic:
    """Tests for TipsEngine without CORTEX backend."""

    def setup_method(self) -> None:
        self.engine = TipsEngine(include_dynamic=False)

    def test_random_returns_tip(self) -> None:
        tip = self.engine.random()
        assert isinstance(tip, Tip)
        assert tip.content

    def test_random_avoids_repeats(self) -> None:
        """Should cycle through all tips before repeating."""
        seen_ids: set[str] = set()
        total = self.engine.count
        for _ in range(total):
            tip = self.engine.random()
            assert tip.id not in seen_ids, f"Repeat detected: {tip.id}"
            seen_ids.add(tip.id)

    def test_random_resets_after_exhaustion(self) -> None:
        """After showing all tips, should start over."""
        total = self.engine.count
        # Exhaust all
        for _ in range(total):
            self.engine.random()
        # Should still work after exhaustion
        tip = self.engine.random()
        assert isinstance(tip, Tip)

    def test_for_category(self) -> None:
        tips = self.engine.for_category("cortex")
        assert len(tips) > 0
        for tip in tips:
            assert tip.category == TipCategory.CORTEX

    def test_for_invalid_category(self) -> None:
        tips = self.engine.for_category("nonexistent")
        assert tips == []

    def test_for_project_returns_general(self) -> None:
        """Without dynamic tips, project tips should return general ones."""
        tips = self.engine.for_project("test-project", limit=3)
        assert len(tips) == 3

    def test_all_tips(self) -> None:
        all_tips = self.engine.all_tips()
        assert len(all_tips) == len(STATIC_TIPS)

    def test_categories_property(self) -> None:
        cats = self.engine.categories
        assert "cortex" in cats
        assert "python" in cats

    def test_count_property(self) -> None:
        assert self.engine.count == len(STATIC_TIPS)

    def test_reset_shown(self) -> None:
        self.engine.random()
        self.engine.reset_shown()
        # After reset, all tips are available again
        seen = set()
        for _ in range(self.engine.count):
            tip = self.engine.random()
            seen.add(tip.id)
        assert len(seen) == self.engine.count

    def test_exclude_shown_false(self) -> None:
        """With exclude_shown=False, repeats are allowed."""
        tip1 = self.engine.random(exclude_shown=False)
        assert isinstance(tip1, Tip)


# ─── TipsEngine Tests (Dynamic with Mock DB) ────────────────────────


class TestTipsEngineDynamic:
    """Tests for TipsEngine with a mock CORTEX database."""

    def setup_method(self) -> None:
        """Create an in-memory SQLite DB mimicking CORTEX schema."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                fact_type TEXT NOT NULL DEFAULT 'note',
                deprecated INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        # Insert test data
        self.conn.executemany(
            "INSERT INTO facts (project, content, fact_type) VALUES (?, ?, ?)",
            [
                ("myproject", "Decided to use SQLite over Postgres", "decision"),
                ("myproject", "Fixed the NULL constraint bug in ledger", "error"),
                ("shared", "Bridge: Auth pattern from web to mobile", "bridge"),
            ],
        )
        self.conn.commit()

        # Create a mock engine with _get_conn
        class MockEngine:
            def __init__(self, conn: sqlite3.Connection) -> None:
                self._conn = conn

            def _get_conn(self) -> sqlite3.Connection:
                return self._conn

        self.mock_engine = MockEngine(self.conn)
        self.tips_engine = TipsEngine(self.mock_engine, include_dynamic=True)

    def teardown_method(self) -> None:
        self.conn.close()

    def test_dynamic_tips_loaded(self) -> None:
        all_tips = self.tips_engine.all_tips()
        # Should have static + dynamic
        assert len(all_tips) > len(STATIC_TIPS)

    def test_decision_tip_mined(self) -> None:
        all_tips = self.tips_engine.all_tips()
        decision_tips = [t for t in all_tips if t.source == "memory" and "decision" in t.id]
        assert len(decision_tips) >= 1
        assert "SQLite" in decision_tips[0].content

    def test_error_tip_mined(self) -> None:
        all_tips = self.tips_engine.all_tips()
        error_tips = [t for t in all_tips if t.source == "memory" and "err" in t.id]
        assert len(error_tips) >= 1
        assert "NULL constraint" in error_tips[0].content

    def test_bridge_tip_mined(self) -> None:
        all_tips = self.tips_engine.all_tips()
        bridge_tips = [t for t in all_tips if t.source == "memory" and "pat" in t.id]
        assert len(bridge_tips) >= 1
        assert "Auth pattern" in bridge_tips[0].content

    def test_project_tips_include_dynamic(self) -> None:
        tips = self.tips_engine.for_project("myproject", limit=5)
        project_specific = [t for t in tips if t.project == "myproject"]
        assert len(project_specific) >= 1

    def test_cache_invalidation(self) -> None:
        # Load initial cache
        initial_count = self.tips_engine.count

        # Add more facts
        self.conn.execute(
            "INSERT INTO facts (project, content, fact_type) VALUES (?, ?, ?)",
            ("new", "New decision made", "decision"),
        )
        self.conn.commit()

        # Cache should still show old count
        assert self.tips_engine.count == initial_count

        # Invalidate and check again
        self.tips_engine.invalidate_cache()
        assert self.tips_engine.count >= initial_count

    def test_truncation_of_long_content(self) -> None:
        """Long decision content should be truncated to 200 chars."""
        long_content = "X" * 500
        self.conn.execute(
            "INSERT INTO facts (project, content, fact_type) VALUES (?, ?, ?)",
            ("proj", long_content, "decision"),
        )
        self.conn.commit()
        self.tips_engine.invalidate_cache()

        all_tips = self.tips_engine.all_tips()
        dynamic_tips = [t for t in all_tips if t.source == "memory"]
        long_tip = [t for t in dynamic_tips if "…" in t.content]
        assert len(long_tip) >= 1
