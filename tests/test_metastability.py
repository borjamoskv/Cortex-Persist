"""CORTEX — Metastability Probing Test Suite.

Tests the immune metastability probe (Axiom Ω₁₃).
Key invariant: "sin anomalías" deja de equivaler a "estable".
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

from cortex.extensions.immune.metastability import (
    assess_metastability,
)


class TestAssessMetastability:
    def test_all_clear_not_fragile(self) -> None:
        """Perfect metrics → no fragility."""
        report = assess_metastability(
            "engine",
            coverage_hot_paths=0.95,
            single_point_dependencies=0,
            untested_fallbacks=0,
            config_implicit=False,
            silent_failure_history=0,
        )
        assert report.fragile_stable_state is False
        assert report.confidence_penalty == 0.0
        assert report.hidden_dependency_score == 0.0
        assert report.reasons == []

    def test_low_coverage_plus_spof_is_fragile(self) -> None:
        """Low coverage + SPOF → exceeds threshold."""
        report = assess_metastability(
            "database",
            coverage_hot_paths=0.3,
            single_point_dependencies=1,
        )
        # 0.30 + 0.20 = 0.50 ≥ 0.45
        assert report.fragile_stable_state is True
        assert report.confidence_penalty == 0.2
        assert report.perturbation_needed is True
        assert len(report.reasons) == 2

    def test_exact_threshold_boundary(self) -> None:
        """Score ≥ 0.45 → fragile. Use SPOF + fallback to get 0.40, then add config for 0.55."""
        # single_point (0.20) + untested_fallback (0.20) + implicit_config (0.15) = 0.55
        report = assess_metastability(
            "boundary",
            single_point_dependencies=1,
            untested_fallbacks=1,
            config_implicit=True,
        )
        assert report.hidden_dependency_score >= 0.45
        assert report.fragile_stable_state is True

    def test_below_threshold_not_fragile(self) -> None:
        """Score < 0.45 → stable."""
        # Only coverage < 0.6 = 0.30
        report = assess_metastability(
            "partial",
            coverage_hot_paths=0.4,
        )
        assert report.hidden_dependency_score == 0.30
        assert report.fragile_stable_state is False
        assert report.confidence_penalty == 0.0

    def test_all_signals_active(self) -> None:
        """All 5 signals → worst case score = 1.0."""
        report = assess_metastability(
            "worst",
            coverage_hot_paths=0.1,
            single_point_dependencies=3,
            untested_fallbacks=2,
            config_implicit=True,
            silent_failure_history=5,
        )
        assert report.hidden_dependency_score == 1.0
        assert report.fragile_stable_state is True
        assert len(report.reasons) == 5

    def test_report_subsystem_name_set(self) -> None:
        report = assess_metastability("search")
        assert report.subsystem == "search"

    def test_default_subsystem(self) -> None:
        report = assess_metastability()
        assert report.subsystem == "default"
