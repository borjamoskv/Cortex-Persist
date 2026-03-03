"""CORTEX v8 — Neuromorphic Pipeline Integration Tests.

End-to-end tests exercising the full pipeline:
  1. Store a fact through SchemaEngine → Valence → STDP
  2. Query with metamemory assessment (FOK/JOL)
  3. Verify void detector classifies correctly
  4. Validate schema-based retrieval augmentation
"""

from __future__ import annotations

from cortex.memory.pipeline import NeuromorphicPipeline, QueryResult, StoreResult
from cortex.memory.void_detector import EpistemicState


# ─── Helpers ──────────────────────────────────────────────────────────


class _FakeEngram:
    """Minimal engram stub for pipeline tests."""

    def __init__(
        self,
        embedding: list[float] | None = None,
        content: str = "test fact",
        energy_level: float = 1.0,
    ):
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.content = content
        self.metadata = {}
        self.entangled_refs: list[str] = []
        self.energy_level = energy_level

    def compute_decay(self) -> float:
        return self.energy_level


def _unit_vec(dim: int = 3, axis: int = 0) -> list[float]:
    v = [0.0] * dim
    v[axis] = 1.0
    return v


# ─── Store Pipeline Tests ────────────────────────────────────────────


class TestStorePipeline:
    """Store path: content → SchemaEngine filter → Valence → STDP."""

    def test_basic_store_returns_result(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="Decided to use AES-256-GCM for encryption",
            fact_type="decision",
            fact_id="fact_001",
        )
        assert isinstance(result, StoreResult)
        assert result.pipeline_ms >= 0

    def test_error_content_gets_negative_valence(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="Error: database connection failed with timeout",
            fact_type="error",
        )
        assert result.valence.valence < 0

    def test_decision_gets_positive_valence(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="We decided to adopt the singleton pattern",
            fact_type="decision",
        )
        assert result.valence.valence > 0

    def test_schema_applied_to_error_content(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="Traceback (most recent call last): ImportError in module X",
            fact_type="error",
        )
        assert result.schema_applied == "error_debugging"

    def test_neutral_content_no_schema(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="The sky is blue today",
            fact_type="knowledge",
        )
        # May or may not match a schema — but valence should be neutral
        assert abs(result.valence.valence) < 0.01

    def test_stdp_records_activations(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="Bridge pattern from project A to B",
            fact_type="bridge",
            fact_id="fact_bridge_1",
            related_fact_ids=["fact_001", "fact_002"],
        )
        assert result.stdp_edges_updated == 3  # 1 main + 2 related
        assert pipe.stdp.node_count >= 1

    def test_store_without_fact_id_skips_stdp(self):
        pipe = NeuromorphicPipeline()
        result = pipe.process_store(
            content="Just a note",
        )
        assert result.stdp_edges_updated == 0


# ─── Query Pipeline Tests ────────────────────────────────────────────


class TestQueryPipeline:
    """Query path: SchemaEngine → VoidDetector → Metamemory."""

    def test_empty_candidates_void(self):
        pipe = NeuromorphicPipeline()
        result = pipe.assess_query(
            query="How does CORTEX handle encryption?",
            query_embedding=_unit_vec(),
            candidates=[],
        )
        assert isinstance(result, QueryResult)
        assert result.epistemic.state == EpistemicState.VOID_ABSOLUTE
        assert not result.safe_to_respond

    def test_high_quality_candidates_confident(self):
        pipe = NeuromorphicPipeline()
        embedding = _unit_vec(3, 0)
        candidates = [
            {"score": 0.95, "content": "AES-256-GCM encryption", "id": "f1"},
            {"score": 0.90, "content": "Encryption at rest", "id": "f2"},
            {"score": 0.85, "content": "TLS in transit", "id": "f3"},
        ]
        engrams = [
            _FakeEngram(embedding=embedding, content="AES-256-GCM encryption"),
            _FakeEngram(embedding=embedding, content="Encryption at rest"),
            _FakeEngram(embedding=embedding, content="TLS in transit"),
        ]
        result = pipe.assess_query(
            query="How does CORTEX handle encryption?",
            query_embedding=embedding,
            candidates=candidates,
            engrams=engrams,
        )
        assert result.epistemic.state == EpistemicState.CONFIDENT
        assert result.safe_to_respond

    def test_schema_augments_error_query(self):
        pipe = NeuromorphicPipeline()
        result = pipe.assess_query(
            query="traceback ImportError",
            query_embedding=_unit_vec(),
            candidates=[],
        )
        assert result.schema_applied == "error_debugging"
        assert "error resolution" in result.augmented_query

    def test_pipeline_latency_measured(self):
        pipe = NeuromorphicPipeline()
        result = pipe.assess_query(
            query="test",
            query_embedding=_unit_vec(),
            candidates=[],
        )
        assert result.pipeline_ms >= 0


# ─── Calibration Feedback Loop Tests ─────────────────────────────────


class TestCalibrationLoop:
    """Verify the retrieval outcome feedback loop works end-to-end."""

    def test_record_outcome_updates_calibration(self):
        pipe = NeuromorphicPipeline()
        # Initially no calibration data
        assert pipe.calibration_score == -1.0

        # Record some outcomes
        for i in range(15):
            pipe.record_retrieval_outcome(
                query=f"query_{i}",
                predicted_confidence=0.8,
                actual_success=i % 2 == 0,  # 50% success rate
            )

        # Now we have enough data for Brier score
        score = pipe.calibration_score
        assert 0.0 <= score <= 1.0

    def test_pipeline_repr(self):
        pipe = NeuromorphicPipeline()
        s = repr(pipe)
        assert "NeuromorphicPipeline" in s
        assert "calibration=" in s
