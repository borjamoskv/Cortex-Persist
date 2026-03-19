"""Tests for CORTEX Intelligence Upgrade — 6 components.

Tests:
1. Inference Engine (inference.py)
2. Contradiction Guard embedding layer
3. Shannon entropy module
4. Temporal decay in hybrid search
5. Metastability probe
6. Embedding cosine similarity helper
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

# ─── 1. Inference Engine ───


class TestInferenceEngine:
    """Test the inference engine's rule-based derivation."""

    def test_inference_rule_dataclass(self):
        """InferenceRule can be instantiated."""
        from cortex.engine.inference import InferenceRule

        rule = InferenceRule(
            name="test",
            description="A test rule",
            condition_sql="SELECT 1",
            conclusion_template="derived: {content}",
        )
        assert rule.name == "test"
        assert rule.min_source_confidence == "C4"

    def test_inference_engine_instantiation(self):
        """InferenceEngine loads builtin rules."""
        from cortex.engine.inference import InferenceEngine

        engine = InferenceEngine()
        assert len(engine.rules) > 0
        rule_names = [r.name for r in engine.rules]
        assert "version_supersession" in rule_names

    def test_derivation_dataclass(self):
        """Derivation object has required fields."""
        from cortex.engine.inference import Derivation

        d = Derivation(
            content="derived fact",
            project="test-project",
            source_fact_ids=[1, 2],
            rule_name="test_rule",
            confidence="C3",
            fact_type="code_ghost",
        )
        assert d.confidence == "C3"
        assert d.source_fact_ids == [1, 2]
        assert d.project == "test-project"


# ─── 2. Contradiction Guard Embedding Layer ───


class TestEmbeddingCosine:
    """Test the cosine similarity helper in contradiction_guard.py."""

    def test_cosine_identical_vectors(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        emb = [1.0, 0.0, 0.0]
        assert abs(_embedding_cosine_similarity(emb, emb) - 1.0) < 1e-6

    def test_cosine_orthogonal_vectors(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(_embedding_cosine_similarity(a, b)) < 1e-6

    def test_cosine_none_input(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        assert _embedding_cosine_similarity(None, [1.0, 0.0]) == 0.0
        assert _embedding_cosine_similarity([1.0, 0.0], None) == 0.0
        assert _embedding_cosine_similarity(None, None) == 0.0

    def test_cosine_empty_vectors(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        assert _embedding_cosine_similarity([], []) == 0.0

    def test_cosine_mismatched_dimensions(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        assert _embedding_cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    def test_cosine_known_value(self):
        from cortex.guards.contradiction_guard import _embedding_cosine_similarity

        a = [3.0, 4.0]
        b = [4.0, 3.0]
        expected = (12.0 + 12.0) / (5.0 * 5.0)  # 24/25 = 0.96
        assert abs(_embedding_cosine_similarity(a, b) - expected) < 1e-6


# ─── 3. Shannon Entropy Module ───


class TestShannonEntropy:
    """Test Shannon entropy computation."""

    def test_shannon_report_fields(self):
        from cortex.shannon.entropy import ShannonReport

        r = ShannonReport(
            total_facts=100,
            total_tokens=1000,
            unique_tokens=500,
            entropy_bits=3.14,
            max_entropy_bits=4.0,
            redundancy_score=0.215,
            exergy_ratio=0.785,
            top_redundant_tokens=[("the", 50)],
        )
        assert r.entropy_bits == 3.14
        assert r.exergy_ratio == 0.785
        assert len(r.top_redundant_tokens) == 1

    def test_diagnose_health_high_redundancy(self):
        from cortex.shannon.entropy import ShannonReport, diagnose_health

        report = ShannonReport(
            total_facts=100,
            total_tokens=1000,
            unique_tokens=100,
            entropy_bits=2.0,
            max_entropy_bits=4.0,
            redundancy_score=0.6,
            exergy_ratio=0.4,
            top_redundant_tokens=[("the", 200)],
        )
        diagnosis = diagnose_health(report)
        assert any("redundan" in rec.lower() for rec in diagnosis)

    def test_diagnose_health_healthy(self):
        from cortex.shannon.entropy import ShannonReport, diagnose_health

        report = ShannonReport(
            total_facts=1000,
            total_tokens=10000,
            unique_tokens=8000,
            entropy_bits=3.8,
            max_entropy_bits=4.0,
            redundancy_score=0.05,
            exergy_ratio=0.95,
            top_redundant_tokens=[],
        )
        diagnosis = diagnose_health(report)
        assert isinstance(diagnosis, list)


# ─── 4. Temporal Decay in Search ───


class TestTemporalDecay:
    """Test _apply_temporal_decay function."""

    def _make_result(self, fact_id, score, created_at_iso):
        from cortex.search.models import SearchResult

        return SearchResult(
            fact_id=fact_id,
            content="test",
            project="test",
            fact_type="fact",
            confidence="C4",
            valid_from=created_at_iso,
            valid_until=None,
            tags=[],
            created_at=created_at_iso,
            updated_at=created_at_iso,
            score=score,
            source="semantic",
        )

    def test_recent_facts_score_higher(self):
        from cortex.search.hybrid import _apply_temporal_decay

        now = datetime.now(timezone.utc)
        recent = self._make_result(1, 0.5, now.isoformat())
        old = self._make_result(2, 0.5, (now - timedelta(days=365)).isoformat())
        results = _apply_temporal_decay([old, recent], recency_weight=0.3)
        # Recent fact should now score higher
        assert results[0].fact_id == 1

    def test_zero_weight_no_change(self):
        from cortex.search.hybrid import _apply_temporal_decay

        now = datetime.now(timezone.utc)
        r = self._make_result(1, 0.5, now.isoformat())
        results = _apply_temporal_decay([r], recency_weight=0.0)
        assert abs(results[0].score - 0.5) < 0.01

    def test_decay_constant_halflife(self):
        """Verify the decay constant gives ~70 day half-life."""
        from cortex.search.hybrid import _DECAY_LAMBDA

        half_life = math.log(2) / _DECAY_LAMBDA
        assert 60 < half_life < 80  # Approximately 70 days


# ─── 5. Metastability Probe ───


class TestMetastabilityProbe:
    """Test metastability probe dataclass and logic."""

    def test_report_fragility_ratio_empty(self):
        from cortex.immune.probe import MetastabilityReport

        r = MetastabilityReport()
        assert r.fragility_ratio == 0.0

    def test_report_fragility_ratio_computed(self):
        from cortex.immune.probe import MetastabilityReport

        r = MetastabilityReport(
            total_probed=100,
            metastable_count=25,
        )
        assert r.fragility_ratio == 0.25

    def test_report_default_lists(self):
        from cortex.immune.probe import MetastabilityReport

        r = MetastabilityReport()
        assert r.metastable_facts == []
        assert r.untested_assumptions == []


# ─── 6. Embedding Boost Weight ───


class TestEmbeddingBoostConstant:
    """Verify EMBEDDING_BOOST_WEIGHT is correctly configured."""

    def test_boost_weight_range(self):
        from cortex.guards.contradiction_guard import EMBEDDING_BOOST_WEIGHT

        assert 0 < EMBEDDING_BOOST_WEIGHT <= 1.0
        assert EMBEDDING_BOOST_WEIGHT == 0.3
