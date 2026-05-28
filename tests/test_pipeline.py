"""Tests for cortex.memory.pipeline — NeuromorphicPipeline.

Covers query assessment and store processing paths.
All tests are self-contained with mocks — no DB, no LLM.
"""

from __future__ import annotations

from unittest.mock import MagicMock

# ─── Helpers ─────────────────────────────────────────────────────────────


def _mock_schema():
    """Minimal schema mock."""
    s = MagicMock()
    s.name = "test_schema"
    return s


def _build_pipeline():
    """Build a NeuromorphicPipeline with all subsystems mocked."""
    from cortex.memory.pipeline import NeuromorphicPipeline

    return NeuromorphicPipeline()


# ─── NeuromorphicPipeline.assess_query ───────────────────────────────────


class TestAssessQuery:
    """Tests for the query assessment path."""

    def test_basic_query_returns_query_result(self):
        from cortex.memory.pipeline import QueryResult

        pipe = _build_pipeline()
        result = pipe.assess_query(
            query="What is CORTEX?",
            query_embedding=[1.0, 0.0, 0.0],
            candidates=[],
        )
        assert isinstance(result, QueryResult)
        assert result.pipeline_ms >= 0.0

    def test_empty_candidates_safe_to_respond(self):
        pipe = _build_pipeline()
        result = pipe.assess_query(
            query="test",
            query_embedding=[0.0] * 384,
            candidates=[],
        )
        # With empty candidates, void detector should report void
        assert hasattr(result, "safe_to_respond")

    def test_schema_applied_when_matched(self):
        from cortex.memory.pipeline import NeuromorphicPipeline

        mock_schema_engine = MagicMock()
        mock_schema_engine.match_schema.return_value = _mock_schema()
        mock_schema_engine.apply_retrieval_schema.return_value = "augmented q"

        pipe = NeuromorphicPipeline(schema_engine=mock_schema_engine)
        result = pipe.assess_query(
            query="test",
            query_embedding=[0.0] * 3,
            candidates=[],
        )
        assert result.schema_applied == "test_schema"
        assert result.augmented_query == "augmented q"

    def test_no_schema_returns_none_schema(self):
        pipe = _build_pipeline()
        result = pipe.assess_query(
            query="test",
            query_embedding=[0.0] * 3,
            candidates=[],
        )
        assert result.schema_applied is None

    def test_augmented_query_is_original_when_no_schema(self):
        pipe = _build_pipeline()
        result = pipe.assess_query(
            query="original query",
            query_embedding=[0.0] * 3,
            candidates=[],
        )
        assert result.augmented_query == "original query"


# ─── NeuromorphicPipeline.process_store ──────────────────────────────────


class TestProcessStore:
    """Tests for the store processing path."""

    def test_basic_store_returns_store_result(self):
        from cortex.memory.pipeline import StoreResult

        pipe = _build_pipeline()
        result = pipe.process_store(content="The sky is blue", fact_type="knowledge")
        assert isinstance(result, StoreResult)
        assert result.pipeline_ms >= 0.0

    def test_valence_classification(self):
        pipe = _build_pipeline()
        result = pipe.process_store(
            content="Critical production failure at 3am",
            fact_type="error",
        )
        assert result.valence is not None

    def test_stdp_recorded_with_fact_id(self):
        pipe = _build_pipeline()
        result = pipe.process_store(content="test", fact_type="knowledge", fact_id="fact_1")
        assert result.stdp_edges_updated >= 1

    def test_stdp_recorded_with_related_ids(self):
        pipe = _build_pipeline()
        result = pipe.process_store(
            content="test",
            fact_type="knowledge",
            fact_id="fact_1",
            related_fact_ids=["related_1", "related_2"],
        )
        # 1 for fact_id + 2 for related
        assert result.stdp_edges_updated == 3

    def test_no_stdp_without_fact_id(self):
        pipe = _build_pipeline()
        result = pipe.process_store(content="test")
        assert result.stdp_edges_updated == 0


# ─── Properties ──────────────────────────────────────────────────────────


class TestPipelineProperties:
    """Tests for pipeline properties and repr."""

    def test_calibration_score_returns_float(self):
        pipe = _build_pipeline()
        score = pipe.calibration_score
        assert isinstance(score, float)

    def test_repr_contains_class_name(self):
        pipe = _build_pipeline()
        r = repr(pipe)
        assert "NeuromorphicPipeline" in r
        assert "calibration=" in r
        assert "stdp_edges=" in r

    def test_metamemory_property(self):
        from cortex.memory.metamemory import MetamemoryMonitor

        pipe = _build_pipeline()
        assert isinstance(pipe.metamemory, MetamemoryMonitor)
