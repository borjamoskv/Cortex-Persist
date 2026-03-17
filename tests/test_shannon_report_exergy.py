"""Integration tests: ExergyReport + dead_weight_bits in EntropyReport.analyze().

Validates Ω₁₃ enforcement: the Shannon report now contains mechanical
exergy evidence, not just entropy measurements.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.shannon.report import EntropyReport


def _make_scanner_mock() -> MagicMock:
    """Build a MemoryScanner mock matching actual method names."""
    scanner = MagicMock()
    scanner.total_active_facts = AsyncMock(return_value=100)
    scanner.type_distribution = AsyncMock(
        return_value={"decision": 40, "error": 10, "pattern": 30, "system": 20}
    )
    scanner.confidence_distribution = AsyncMock(
        return_value={"C5": 50, "C4": 30, "C3": 15, "C2": 5}
    )
    scanner.project_distribution = AsyncMock(
        return_value={"cortex": 60, "naroa": 40}
    )
    scanner.source_distribution = AsyncMock(
        return_value={"agent": 70, "human": 30}
    )
    scanner.age_distribution = AsyncMock(
        return_value={"<7d": 20, "7-30d": 30, "30-90d": 30, ">90d": 20}
    )
    scanner.content_length_distribution = AsyncMock(
        return_value={"short": 25, "medium": 50, "long": 25}
    )
    scanner.temporal_velocity = AsyncMock(return_value={
        "2026-03-10": 5, "2026-03-11": 8, "2026-03-12": 12,
        "2026-03-13": 10, "2026-03-14": 15, "2026-03-15": 20,
        "2026-03-16": 18,
    })
    scanner.type_project_joint = AsyncMock(
        return_value={
            ("decision", "cortex"): 25,
            ("decision", "naroa"): 15,
            ("error", "cortex"): 5,
            ("error", "naroa"): 5,
            ("pattern", "cortex"): 20,
            ("pattern", "naroa"): 10,
            ("system", "cortex"): 10,
            ("system", "naroa"): 10,
        }
    )
    return scanner


@pytest.mark.asyncio
async def test_analyze_includes_exergy_report():
    """EntropyReport.analyze() must include exergy_report dict."""
    report = EntropyReport()
    scanner = _make_scanner_mock()
    engine_mock = MagicMock()

    with patch(
        "cortex.extensions.shannon.report.MemoryScanner", return_value=scanner
    ):
        result = await report.analyze(engine_mock)

    assert "exergy_report" in result
    er = result["exergy_report"]
    required_keys = {
        "entropy_score",
        "compression_ratio",
        "exergy_score",
        "downstream_utility",
        "noise_fraction",
        "useful_work_ratio",
    }
    assert required_keys <= set(er.keys()), (
        f"Missing keys: {required_keys - set(er.keys())}"
    )
    for k, v in er.items():
        assert isinstance(v, (int, float)), (
            f"{k} should be numeric, got {type(v)}"
        )


@pytest.mark.asyncio
async def test_analyze_includes_dead_weight_bits():
    """EntropyReport.analyze() must include dead_weight_bits."""
    report = EntropyReport()
    scanner = _make_scanner_mock()
    engine_mock = MagicMock()

    with patch(
        "cortex.extensions.shannon.report.MemoryScanner", return_value=scanner
    ):
        result = await report.analyze(engine_mock)

    assert "dead_weight_bits" in result
    assert isinstance(result["dead_weight_bits"], float)
    assert result["dead_weight_bits"] >= 0.0


@pytest.mark.asyncio
async def test_exergy_report_nonzero_for_real_distributions():
    """With non-trivial distributions, exergy_score should be > 0."""
    report = EntropyReport()
    scanner = _make_scanner_mock()
    engine_mock = MagicMock()

    with patch(
        "cortex.extensions.shannon.report.MemoryScanner", return_value=scanner
    ):
        result = await report.analyze(engine_mock)

    assert result["exergy_score"] > 0.0
    assert result["exergy_report"]["exergy_score"] > 0.0
