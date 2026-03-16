"""Tests for exergy scoring in Shannon analyzer — Ω₁₃ §15.9."""

from __future__ import annotations

import pytest

from cortex.shannon.analyzer import dead_weight, exergy_ratio, exergy_score

# Default usage weights per fact type
DEFAULT_WEIGHTS: dict[str, float] = {
    "decision": 1.0,
    "axiom": 0.9,
    "bridge": 0.7,
    "error": 0.5,
    "ghost": 0.3,
    "discovery": 0.6,
}


class TestExergyScore:
    def test_uniform_full_weight(self) -> None:
        """All categories equally used at weight 1.0 → exergy ≈ 1.0."""
        dist = {"a": 25, "b": 25, "c": 25, "d": 25}
        weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
        score = exergy_score(dist, weights)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_zero_weight(self) -> None:
        """Nothing actionable → exergy = 0."""
        dist = {"a": 50, "b": 50}
        weights = {"a": 0.0, "b": 0.0}
        score = exergy_score(dist, weights)
        assert score == 0.0

    def test_mixed_weights(self) -> None:
        """Mixed weights → exergy between 0 and 1."""
        dist = {"decision": 10, "ghost": 90}
        score = exergy_score(dist, DEFAULT_WEIGHTS)
        assert 0.0 < score < 1.0

    def test_empty_distribution(self) -> None:
        """Empty distribution → exergy = 0."""
        assert exergy_score({}, DEFAULT_WEIGHTS) == 0.0

    def test_single_category(self) -> None:
        """Single category with weight=1 → exergy = 0 (entropy is 0)."""
        dist = {"decision": 100}
        weights = {"decision": 1.0}
        # Entropy of single category = 0, so exergy = 0
        assert exergy_score(dist, weights) == 0.0


class TestExergyRatio:
    def test_bounds(self) -> None:
        """Ratio always ∈ [0, 1]."""
        dist = {"decision": 30, "ghost": 70}
        ratio = exergy_ratio(dist, DEFAULT_WEIGHTS)
        assert 0.0 <= ratio <= 1.0

    def test_full_weight_ratio(self) -> None:
        """All weights = 1.0 → ratio = 1.0."""
        dist = {"a": 25, "b": 25, "c": 25, "d": 25}
        weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
        ratio = exergy_ratio(dist, weights)
        assert ratio == pytest.approx(1.0, abs=0.01)

    def test_zero_entropy(self) -> None:
        """Zero entropy → ratio = 0."""
        dist = {"a": 100}
        weights = {"a": 1.0}
        assert exergy_ratio(dist, weights) == 0.0


class TestDeadWeight:
    def test_positive(self) -> None:
        """Dead weight always ≥ 0."""
        dist = {"decision": 10, "ghost": 90}
        dw = dead_weight(dist, DEFAULT_WEIGHTS)
        assert dw >= 0.0

    def test_zero_for_full_utility(self) -> None:
        """All fully weighted → dead weight ≈ 0."""
        dist = {"a": 25, "b": 25, "c": 25, "d": 25}
        weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
        dw = dead_weight(dist, weights)
        assert dw == pytest.approx(0.0, abs=0.01)

    def test_high_for_noise(self) -> None:
        """Low-utility distributions have lower exergy ratio than high-utility ones."""
        # For same entropy level, the one with lower weights has more dead weight
        # Use equal distributions to hold entropy constant
        dist = {"a": 50, "b": 50}
        high_utility_weights = {"a": 1.0, "b": 1.0}
        low_utility_weights = {"a": 0.1, "b": 0.1}

        dw_useful = dead_weight(dist, high_utility_weights)
        dw_noise = dead_weight(dist, low_utility_weights)

        # Same entropy, but low utility → more dead weight
        assert dw_noise > dw_useful

    def test_empty(self) -> None:
        """Empty distribution → dead weight = 0."""
        assert dead_weight({}, DEFAULT_WEIGHTS) == 0.0
