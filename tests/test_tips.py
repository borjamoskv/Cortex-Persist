"""Tests for cortex.tips module."""

from __future__ import annotations

import sqlite3

import pytest

from cortex.tips import (
    Tip,
    TipCategory,
    TipsEngine,
    _load_static_tips,
)

# ─── Tip Model Tests ────────────────────────────────────────────────


class TestTipModel:
    """Tests for the Tip dataclass."""

    def test_create_tip(self) -> None:
        tip = Tip(id="test1", content="Hello", category=TipCategory.CORTEX, lang="es")
        assert tip.id == "test1"
        assert tip.content == "Hello"
        assert tip.category == TipCategory.CORTEX
        assert tip.lang == "es"
        assert tip.source == "static"
        assert tip.project is None
        assert tip.relevance == pytest.approx(1.0)

    def test_format_with_category(self) -> None:
        tip = Tip(id="t1", content="Do X", category=TipCategory.PYTHON)
        formatted = tip.format(with_category=True)
        assert "💡" in formatted
        assert "[python]" in formatted
        assert "Do X" in formatted


# ─── Static Tips Bank Tests ─────────────────────────────────────────


class TestStaticTips:
    """Tests for the static tips bank."""

    def test_static_tips_not_empty(self) -> None:
        assert len(_load_static_tips()) > 0

    def test_multi_language_support(self) -> None:
        tips = _load_static_tips()
        langs = {t.lang for t in tips}
        assert "en" in langs
        assert "es" in langs

    def test_all_tips_have_unique_ids(self) -> None:
        # IDs are unique per (content + cat + lang)
        tips = _load_static_tips()
        ids = [t.id for t in tips]
        assert len(ids) == len(set(ids)), "Duplicate tip IDs found"


# ─── TipsEngine Tests (Static Only) ─────────────────────────────────


class TestTipsEngineStatic:
    """Tests for TipsEngine without CORTEX backend."""

    def setup_method(self) -> None:
        self.engine_en = TipsEngine(include_dynamic=False, lang="en")
        self.engine_es = TipsEngine(include_dynamic=False, lang="es")

    def test_random_returns_correct_lang(self) -> None:
        tip_en = self.engine_en.random()
        assert tip_en.lang == "en"
        tip_es = self.engine_es.random()
        assert tip_es.lang == "es"

    def test_fallback_to_english(self) -> None:
        # 'eu' (basque) has no static tips currently, should fallback to 'en'
        engine_eu = TipsEngine(include_dynamic=False, lang="eu")
        tip = engine_eu.random()
        assert tip.lang == "en"

    def test_for_category_with_lang(self) -> None:
        tips = self.engine_es.for_category("workflow")
        assert len(tips) > 0
        for tip in tips:
            assert tip.lang == "es"
            assert tip.category == TipCategory.WORKFLOW

    def test_all_tips_filtered_by_lang(self) -> None:
        all_en = self.engine_en.all_tips()
        for t in all_en:
            assert t.lang == "en"


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

        # Create a mock engine with _get_sync_conn
        class MockEngine:
            def __init__(self, conn: sqlite3.Connection) -> None:
                self._conn = conn

            def _get_sync_conn(self) -> sqlite3.Connection:
                return self._conn

        self.mock_engine = MockEngine(self.conn)
        self.tips_engine = TipsEngine(self.mock_engine, include_dynamic=True, lang="en")

    def teardown_method(self) -> None:
        self.conn.close()

    def test_dynamic_tips_loaded(self) -> None:
        all_tips = self.tips_engine.all_tips()
        # Should have static (en) + dynamic
        assert len(all_tips) > 0
        assert any(t.source == "memory" for t in all_tips)

    def test_decision_tip_mined(self) -> None:
        all_tips = self.tips_engine.all_tips()
        decision_tips = [t for t in all_tips if t.source == "memory" and "dec-" in t.id]
        assert len(decision_tips) >= 1
        assert "SQLite" in decision_tips[0].content

    def test_project_tips_include_dynamic(self) -> None:
        tips = self.tips_engine.for_project("myproject", limit=10)
        project_specific = [t for t in tips if t.project == "myproject"]
        assert len(project_specific) >= 1

    def test_cache_invalidation(self) -> None:
        # Load initial cache
        self.tips_engine.all_tips()
        initial_cache_len = len(self.tips_engine._dynamic_cache)

        # Add more facts
        self.conn.execute(
            "INSERT INTO facts (project, content, fact_type) VALUES (?, ?, ?)",
            ("new", "New decision made", "decision"),
        )
        self.conn.commit()

        # Cache should still show old size
        assert len(self.tips_engine._dynamic_cache) == initial_cache_len

        # Invalidate and check again
        self.tips_engine.invalidate_cache()
        self.tips_engine.all_tips()  # Trigger refresh
        assert len(self.tips_engine._dynamic_cache) > initial_cache_len
