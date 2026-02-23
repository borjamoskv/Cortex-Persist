"""Tests for the sovereign power-level engine and observability module."""
from __future__ import annotations

import pytest

from cortex.sovereign.observability import (
    Dimension,
    DimensionScore,
    PowerLevel,
    compute_power,
)


class TestDimensionScore:
    def test_weighted_calculation(self) -> None:
        ds = DimensionScore(dimension=Dimension.INTEGRITY, raw=100.0, multiplier=1.3)
        assert ds.weighted == 130.0

    def test_zero_raw(self) -> None:
        ds = DimensionScore(dimension=Dimension.SECURITY, raw=0.0, multiplier=1.3)
        assert ds.weighted == 0.0


class TestPowerLevel:
    def test_empty_power(self) -> None:
        pl = PowerLevel()
        assert pl.power == 0

    def test_perfect_scores_exceed_1000(self) -> None:
        """130/100 across all 13 dimensions → power > 1000."""
        scores = {dim.value: 100.0 for dim in Dimension}
        power = compute_power(scores, multiplier=1.3)
        assert power.power == 1300
        assert power.power > 1000

    def test_baseline_scores_equal_1000(self) -> None:
        """100/100 across all 13 dimensions with 1.0 multiplier → exactly 1000."""
        scores = {dim.value: 100.0 for dim in Dimension}
        power = compute_power(scores, multiplier=1.0)
        assert power.power == 1000

    def test_partial_scores(self) -> None:
        """Half scores → power ~ 650."""
        scores = {dim.value: 50.0 for dim in Dimension}
        power = compute_power(scores, multiplier=1.3)
        assert power.power == 650

    def test_to_dict(self) -> None:
        scores = {dim.value: 100.0 for dim in Dimension}
        power = compute_power(scores)
        d = power.to_dict()
        assert d["power_level"] == 1300
        assert d["exceeds_theoretical_limit"] is True
        assert "dimensions" in d
        assert len(d["dimensions"]) == 13


class TestComputePower:
    def test_default_multiplier(self) -> None:
        scores = {dim.value: 80.0 for dim in Dimension}
        power = compute_power(scores)
        # 80 * 1.3 = 104 per dim → 104*13 = 1352 weighted
        # power = 1352 / 1300 * 1000 = 1040
        assert power.power == 1040
        assert power.power > 1000

    def test_missing_dimensions_default_zero(self) -> None:
        power = compute_power({})
        assert power.power == 0

    def test_single_dimension(self) -> None:
        power = compute_power({"integrity": 100.0}, multiplier=1.0)
        # Only integrity=100, rest=0 → raw=100, base=1300 → power=76
        assert power.power == 76
