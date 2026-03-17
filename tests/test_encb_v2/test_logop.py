"""Tests for logop.py — Log-odds pooling."""

from __future__ import annotations

from benchmarks.encb.logop import (
    effective_confidence,
    logit,
    robust_scalar_aggregate,
    scored_set_aggregate,
    sigmoid,
    weighted_logop_binary,
    weighted_logop_categorical,
)


class TestLogitSigmoid:
    """Test log-odds transforms."""

    def test_logit_half(self):
        assert abs(logit(0.5)) < 1e-6

    def test_sigmoid_zero(self):
        assert abs(sigmoid(0.0) - 0.5) < 1e-6

    def test_roundtrip(self):
        for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
            assert abs(sigmoid(logit(p)) - p) < 1e-6

    def test_logit_clamps(self):
        # Should not raise for extreme values
        assert logit(0.0) < -10
        assert logit(1.0) > 10

    def test_sigmoid_clamps(self):
        assert sigmoid(1000) == 1.0
        assert sigmoid(-1000) == 0.0


class TestEffectiveConfidence:
    """Test confidence decomposition."""

    def test_all_high(self):
        c = effective_confidence(0.95, 0.95, 0.95, 0.95, 0.95)
        assert c > 0.8

    def test_all_low(self):
        c = effective_confidence(0.1, 0.1, 0.1, 0.1, 0.1)
        assert c < 0.3

    def test_clamps(self):
        c = effective_confidence(1.0, 1.0, 1.0, 1.0, 1.0)
        assert c <= 0.99
        c = effective_confidence(0.0, 0.0, 0.0, 0.0, 0.0)
        assert c >= 0.01


class TestWeightedLogopBinary:
    """Test binary LogOP."""

    def test_unanimous_true(self):
        obs = [(True, 0.9, 0.9), (True, 0.8, 0.8), (True, 0.85, 0.85)]
        val, prob = weighted_logop_binary(obs)
        assert val is True
        assert prob > 0.8

    def test_unanimous_false(self):
        obs = [(False, 0.9, 0.9), (False, 0.8, 0.8)]
        val, prob = weighted_logop_binary(obs)
        assert val is False
        assert prob < 0.2

    def test_mixed_majority_wins(self):
        obs = [
            (True, 0.9, 0.9),
            (True, 0.8, 0.9),
            (False, 0.6, 0.3),  # low reliability liar
        ]
        val, prob = weighted_logop_binary(obs)
        assert val is True

    def test_empty(self):
        val, prob = weighted_logop_binary([])
        assert val is True
        assert prob == 0.5

    def test_low_reliability_liar_discounted(self):
        """Critical: a liar with low reliability should be discounted."""
        obs = [
            (True, 0.7, 0.9),  # honest high-rel
            (False, 0.95, 0.1),  # liar with degraded reliability
        ]
        val, prob = weighted_logop_binary(obs)
        assert val is True  # honest node should prevail


class TestWeightedLogopCategorical:
    """Test categorical LogOP."""

    def test_strong_consensus(self):
        cats = ["a", "b", "c"]
        obs = [("a", 0.9, 0.9), ("a", 0.85, 0.85), ("b", 0.3, 0.2)]
        val, conf = weighted_logop_categorical(obs, cats)
        assert val == "a"

    def test_empty(self):
        val, conf = weighted_logop_categorical([], ["a", "b"])
        assert val == "a"
        assert conf == 0.0


class TestRobustScalarAggregate:
    """Test robust scalar aggregation."""

    def test_agrees(self):
        obs = [(100.0, 0.9, 0.9), (101.0, 0.85, 0.85), (99.0, 0.8, 0.8)]
        val, conf = robust_scalar_aggregate(obs)
        assert 95 < val < 105

    def test_outlier_trimmed(self):
        obs = [
            (100.0, 0.9, 0.9),
            (101.0, 0.9, 0.9),
            (99.0, 0.9, 0.9),
            (100.5, 0.9, 0.9),
            (1000.0, 0.5, 0.1),  # outlier
        ]
        val, conf = robust_scalar_aggregate(obs, trim_fraction=0.2)
        assert val < 200  # outlier should be trimmed

    def test_empty(self):
        val, conf = robust_scalar_aggregate([])
        assert val == 0.0
        assert conf == 0.0


class TestScoredSetAggregate:
    """Test set aggregation."""

    def test_unanimous(self):
        obs = [
            ({"a", "b"}, 0.9, 0.9, 1),
            ({"a", "b"}, 0.85, 0.85, 2),
        ]
        val, conf = scored_set_aggregate(obs)
        assert "a" in val
        assert "b" in val

    def test_empty(self):
        val, conf = scored_set_aggregate([])
        assert val == set()
        assert conf == 0.0
