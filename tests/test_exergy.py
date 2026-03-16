"""CORTEX — Exergy Scoring Test Suite.

Tests the shannon exergy engine (Axiom Ω₁₃).
Key invariant: "más datos" no implica mejor exergy_score.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

import pytest

from cortex.shannon.exergy import ExergyReport, compute_exergy_report


class TestComputeExergyReport:
    def test_high_utility_high_exergy(self) -> None:
        """Useful and compressible → high score."""
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
        """Noisy with no utility → low score."""
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
        """Division by zero protection."""
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
        """Same inputs, higher noise → lower score."""
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
        """Abundant but ornamental content scores worse than compact useful content."""
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
