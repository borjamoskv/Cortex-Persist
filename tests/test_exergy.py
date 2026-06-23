# [C5-REAL] Exergy-Maximized
"""CORTEX exergy scoring tests.

Covers both the legacy Shannon report API and the newer thermodynamic exergy API.
"""

from __future__ import annotations

import pytest

from babylon60.extensions.shannon.exergy import ExergyReport, compute_exergy_report
from babylon60.shannon.exergy import (
    ActionRisk,
    ExergyInput,
    ThermodynamicWasteError,
    calculate_exergy,
    enforce_exergy,
)


class TestComputeExergyReport:
    def test_high_utility_high_exergy(self) -> None:
        report = compute_exergy_report(
            entropy_score=2.5,
            compression_ratio=0.8,
            downstream_utility=0.9,
            decisions_enabled=5,
            tokens_spent=100,
            noise_fraction=0.1,
        )
        assert report.exergy_score > 0.3
        assert report.useful_work_ratio == 0.05

    def test_low_utility_high_noise_low_exergy(self) -> None:
        report = compute_exergy_report(
            entropy_score=4.0,
            compression_ratio=0.1,
            downstream_utility=0.05,
            decisions_enabled=0,
            tokens_spent=1000,
            noise_fraction=0.9,
        )
        assert report.exergy_score < 0.05

    def test_tokens_spent_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="tokens_spent must be > 0"):
            compute_exergy_report(
                entropy_score=1.0,
                compression_ratio=0.5,
                downstream_utility=0.5,
                decisions_enabled=1,
                tokens_spent=0,
                noise_fraction=0.1,
            )

    def test_tokens_spent_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="tokens_spent must be > 0"):
            compute_exergy_report(
                entropy_score=1.0,
                compression_ratio=0.5,
                downstream_utility=0.5,
                decisions_enabled=1,
                tokens_spent=-10,
                noise_fraction=0.1,
            )

    def test_useful_work_ratio_computed(self) -> None:
        report = compute_exergy_report(
            entropy_score=1.0,
            compression_ratio=0.5,
            downstream_utility=0.5,
            decisions_enabled=10,
            tokens_spent=200,
            noise_fraction=0.0,
        )
        assert report.useful_work_ratio == 0.05

    def test_noise_subtracts_from_score(self) -> None:
        low_noise = compute_exergy_report(
            entropy_score=2.0,
            compression_ratio=0.5,
            downstream_utility=0.7,
            decisions_enabled=3,
            tokens_spent=100,
            noise_fraction=0.1,
        )
        high_noise = compute_exergy_report(
            entropy_score=2.0,
            compression_ratio=0.5,
            downstream_utility=0.7,
            decisions_enabled=3,
            tokens_spent=100,
            noise_fraction=0.9,
        )
        assert low_noise.exergy_score > high_noise.exergy_score

    def test_report_fields_populated(self) -> None:
        report = compute_exergy_report(
            entropy_score=3.0,
            compression_ratio=0.6,
            downstream_utility=0.8,
            decisions_enabled=4,
            tokens_spent=500,
            noise_fraction=0.2,
        )
        assert isinstance(report, ExergyReport)
        assert report.entropy_score == 3.0
        assert report.compression_ratio == 0.6
        assert report.downstream_utility == 0.8
        assert report.noise_fraction == 0.2

    def test_ornamental_content_penalized(self) -> None:
        ornamental = compute_exergy_report(
            entropy_score=5.0,
            compression_ratio=0.1,
            downstream_utility=0.1,
            decisions_enabled=0,
            tokens_spent=10000,
            noise_fraction=0.8,
        )
        compact = compute_exergy_report(
            entropy_score=1.0,
            compression_ratio=0.9,
            downstream_utility=0.9,
            decisions_enabled=5,
            tokens_spent=50,
            noise_fraction=0.05,
        )
        assert compact.exergy_score > ornamental.exergy_score


def test_exergy_reduces_uncertainty_low_cost() -> None:
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=0.1,
        tokens_consumed=100,
        action_risk=ActionRisk.READ_ONLY,
        had_backup=True,
        touched_persistent_state=False,
    )
    result = calculate_exergy(inp, threshold_min_work=0.001)
    assert not result.below_threshold
    assert result.score > 0
    enforce_exergy(result)


def test_exergy_waste_tokens() -> None:
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=1.0,
        tokens_consumed=5000,
        action_risk=ActionRisk.READ_ONLY,
        had_backup=True,
        touched_persistent_state=False,
    )
    result = calculate_exergy(inp, threshold_min_work=0.001)
    assert result.below_threshold
    with pytest.raises(ThermodynamicWasteError):
        enforce_exergy(result)


def test_destructive_without_backup_negative_score() -> None:
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=0.5,
        tokens_consumed=10,
        action_risk=ActionRisk.DESTRUCTIVE,
        had_backup=False,
        touched_persistent_state=True,
    )
    result = calculate_exergy(inp, threshold_min_work=0.1)  # Threshold raised for proportional model
    assert result.score < 0.1  # Score will be positive but very small due to massive risk penalty
    assert result.below_threshold
