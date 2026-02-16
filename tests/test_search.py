"""
CORTEX v4.0 — Search Module Tests.

Tests for text_search edge cases: empty results, project filtering,
type filtering, limit enforcement.
"""

import json
import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.search import text_search


@pytest.fixture
def search_engine():
    """Create a temporary engine with test data for search tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    eng.init_db()

    # Insert varied test data
    eng.store("alpha", "Python is a great language", fact_type="knowledge", tags=["python"])
    eng.store("alpha", "Use pytest for testing", fact_type="decision", tags=["testing"])
    eng.store("beta", "Python supports async/await", fact_type="knowledge", tags=["python"])
    eng.store("beta", "Rust is fast", fact_type="knowledge", tags=["rust"])
    eng.store("gamma", "Deploy with Docker", fact_type="decision", tags=["devops"])

    yield eng
    eng.close()
    os.unlink(db_path)


class TestTextSearch:
    def test_finds_matching_content(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "Python")
        assert len(results) >= 2
        assert all("Python" in r.content for r in results)

    def test_no_results_for_unmatched_query(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "xyznonexistent")
        assert results == []

    def test_project_filter(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "Python", project="alpha")
        assert len(results) == 1
        assert results[0].project == "alpha"

    def test_fact_type_filter(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "Python", fact_type="decision")
        assert results == []  # No "Python" in decision-type facts for alpha

    def test_limit_enforcement(self, search_engine):
        conn = search_engine._get_conn()
        # Insert enough data to test the limit
        for i in range(10):
            search_engine.store("alpha", f"Extra Python fact {i}", fact_type="knowledge")
        results = text_search(conn, "Python", limit=3)
        assert len(results) <= 3

    def test_result_has_correct_score(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "Docker")
        assert len(results) == 1
        assert results[0].score == 0.5  # Flat score for text search

    def test_result_has_tags(self, search_engine):
        conn = search_engine._get_conn()
        results = text_search(conn, "Docker")
        assert results[0].tags == ["devops"]

    def test_deprecated_facts_excluded(self, search_engine):
        """Deprecated facts (valid_until IS NOT NULL) should not appear."""
        search_engine.deprecate(1)
        conn = search_engine._get_conn()
        results = text_search(conn, "Python")
        fact_ids = {r.fact_id for r in results}
        assert 1 not in fact_ids
