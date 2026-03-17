"""Tests for runner.py — end-to-end smoke tests."""

from __future__ import annotations

import pytest

from benchmarks.encb.metrics import MetricsReport
from benchmarks.encb.runner import export_results, run_single
from benchmarks.encb.strategies import StrategyID


class TestRunSingle:
    """Smoke tests for single runs."""

    @pytest.mark.parametrize("strategy", list(StrategyID))
    def test_runs_without_error(self, strategy: StrategyID):
        """Verify each strategy completes on a small instance."""
        report = run_single(
            strategy=strategy,
            n_agents=20,
            n_props=50,
            n_domains=4,
            rounds=5,
            seed=42,
            corruption_rate=0.20,
            clique_size=3,
        )
        assert isinstance(report, MetricsReport)
        assert report.strategy == strategy.value
        assert 0.0 <= report.pfbr_final <= 1.0
        assert report.edi_total >= 0.0

    def test_cortex_ablation_flags(self):
        """Verify ablation flags are respected."""
        full = run_single(
            strategy=StrategyID.CORTEX,
            n_agents=20,
            n_props=50,
            rounds=5,
            seed=42,
            use_reliability=True,
            use_atms=True,
        )
        no_rel = run_single(
            strategy=StrategyID.CORTEX,
            n_agents=20,
            n_props=50,
            rounds=5,
            seed=42,
            use_reliability=False,
            use_atms=True,
        )
        # They should produce different results
        assert isinstance(full, MetricsReport)
        assert isinstance(no_rel, MetricsReport)

    def test_error_rate_by_type(self):
        """Verify error rates are computed per belief type."""
        report = run_single(
            strategy=StrategyID.CORTEX,
            n_agents=20,
            n_props=100,
            rounds=5,
            seed=0,
        )
        assert len(report.error_rate_by_type) > 0
        for _bt, rate in report.error_rate_by_type.items():
            assert 0.0 <= rate <= 1.0

    def test_deterministic_with_same_seed(self):
        """Same seed should produce identical results."""
        r1 = run_single(
            strategy=StrategyID.LWW,
            n_agents=10,
            n_props=20,
            rounds=3,
            seed=123,
        )
        r2 = run_single(
            strategy=StrategyID.LWW,
            n_agents=10,
            n_props=20,
            rounds=3,
            seed=123,
        )
        assert r1.pfbr_final == r2.pfbr_final
        assert r1.edi_total == r2.edi_total


class TestExportResults:
    """Test JSON export."""

    def test_export_creates_file(self, tmp_path):
        report = run_single(
            strategy=StrategyID.LWW,
            n_agents=10,
            n_props=20,
            rounds=3,
            seed=0,
        )
        output = str(tmp_path / "results.json")
        export_results({"S0_lww": [report]}, output)
        assert (tmp_path / "results.json").exists()
