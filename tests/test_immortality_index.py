"""Tests for ImmortalityIndex — cognitive crystallization metric."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture()
def mock_scanner():
    """Patch MemoryScanner to return controlled data."""
    with patch("cortex.shannon.immortality.MemoryScanner") as mock_cls:
        scanner = AsyncMock()
        mock_cls.return_value = scanner
        yield scanner


@pytest.mark.asyncio
async def test_immortality_empty_db(mock_scanner):
    """Zero facts → ι = 0%, diagnosis = entropic_decay_risk."""
    mock_scanner.total_active_facts.return_value = 0
    mock_scanner.type_distribution.return_value = {}
    mock_scanner.temporal_gap_days.return_value = (0.0, 1.0, 0)
    mock_scanner.confidence_weight_sum.return_value = (0.0, 1)
    mock_scanner.domain_coverage.return_value = (0, 1)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    assert result["iota"] == 0.0
    assert result["iota_pct"] == 0.0
    assert result["diagnosis"] == "entropic_decay_risk"
    assert result["total_facts"] == 0
    assert "dimensions" in result
    assert "weakest" in result


@pytest.mark.asyncio
async def test_immortality_perfect_score(mock_scanner):
    """All dimensions maxed → ι ≈ 100%."""
    # Perfectly uniform type distribution (max normalized entropy)
    mock_scanner.total_active_facts.return_value = 500
    mock_scanner.type_distribution.return_value = {
        "decision": 100,
        "error": 100,
        "ghost": 100,
        "bridge": 100,
        "discovery": 100,
    }
    # No gaps, 100 active days over 100 day span
    mock_scanner.temporal_gap_days.return_value = (1.0, 100.0, 100)
    # All C5 confidence
    mock_scanner.confidence_weight_sum.return_value = (500.0, 500)
    # Full domain coverage
    mock_scanner.domain_coverage.return_value = (25, 25)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    assert result["iota"] >= 0.90
    assert result["diagnosis"] == "approaching_functional_immortality"
    assert result["iota_pct"] >= 90.0


@pytest.mark.asyncio
async def test_immortality_single_weak_dimension(mock_scanner):
    """One dimension at 0, rest high → ι is dragged down."""
    mock_scanner.total_active_facts.return_value = 200
    # Single type = zero normalized entropy
    mock_scanner.type_distribution.return_value = {"decision": 200}
    mock_scanner.temporal_gap_days.return_value = (1.0, 60.0, 60)
    mock_scanner.confidence_weight_sum.return_value = (200.0, 200)
    mock_scanner.domain_coverage.return_value = (10, 10)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    # Diversity should be ~0 (single category = 0 entropy)
    assert result["dimensions"]["diversity"]["score"] < 0.01
    assert result["weakest"]["dimension"] == "diversity"
    # Composite should be visibly lower than perfect
    assert result["iota"] < 0.80


@pytest.mark.asyncio
async def test_continuity_large_gap(mock_scanner):
    """Large temporal gap → low continuity score."""
    mock_scanner.total_active_facts.return_value = 100
    mock_scanner.type_distribution.return_value = {
        "decision": 50,
        "error": 50,
    }
    # 80-day gap in 100-day span → continuity = 1 - 80/100 = 0.2
    mock_scanner.temporal_gap_days.return_value = (80.0, 100.0, 10)
    mock_scanner.confidence_weight_sum.return_value = (80.0, 100)
    mock_scanner.domain_coverage.return_value = (5, 10)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    cont = result["dimensions"]["continuity"]["score"]
    assert cont == pytest.approx(0.2, abs=0.01)


@pytest.mark.asyncio
async def test_confidence_weighting(mock_scanner):
    """Mix of C1-C5 → verify quality dimension."""
    mock_scanner.total_active_facts.return_value = 100
    mock_scanner.type_distribution.return_value = {
        "decision": 50,
        "error": 50,
    }
    mock_scanner.temporal_gap_days.return_value = (1.0, 30.0, 30)
    # 50 C1 (0.2 each) + 50 C5 (1.0 each) = 10 + 50 = 60 / 100 = 0.6
    mock_scanner.confidence_weight_sum.return_value = (60.0, 100)
    mock_scanner.domain_coverage.return_value = (5, 10)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    quality = result["dimensions"]["quality"]["score"]
    assert quality == pytest.approx(0.6, abs=0.01)


@pytest.mark.asyncio
async def test_json_output_structure(mock_scanner):
    """Verify all expected keys in output dict."""
    mock_scanner.total_active_facts.return_value = 10
    mock_scanner.type_distribution.return_value = {"decision": 10}
    mock_scanner.temporal_gap_days.return_value = (1.0, 5.0, 5)
    mock_scanner.confidence_weight_sum.return_value = (8.0, 10)
    mock_scanner.domain_coverage.return_value = (1, 1)

    from cortex.shannon.immortality import ImmortalityIndex

    engine = AsyncMock()
    result = await ImmortalityIndex.compute(engine)

    expected_keys = {
        "iota",
        "iota_pct",
        "diagnosis",
        "badge",
        "total_facts",
        "active_days",
        "total_span_days",
        "max_gap_days",
        "project_filter",
        "dimensions",
        "weakest",
    }
    assert expected_keys == set(result.keys())

    dim_keys = {"diversity", "continuity", "density", "quality", "coverage"}
    assert dim_keys == set(result["dimensions"].keys())

    for dim in result["dimensions"].values():
        assert {"score", "pct", "bar", "weight"} == set(dim.keys())

    assert {"dimension", "score", "recommendation"} == set(result["weakest"].keys())
