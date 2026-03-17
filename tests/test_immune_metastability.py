"""Tests for metastability probe — Ω₁₃ §15.9."""

from __future__ import annotations

from cortex.extensions.immune.metastability import assess_metastability


def test_dormant_system_detected() -> None:
    """Zero recent facts but high confidence triggers fragile stable state."""
    report = assess_metastability(
        subsystem="test_dormant",
        coverage_hot_paths=0.4,
        untested_fallbacks=2,
    )

    assert report.fragile_stable_state is True
    assert report.hidden_dependency_score >= 0.45
    assert report.confidence_penalty == 0.2
    assert report.perturbation_needed is True


def test_healthy_system_passes() -> None:
    """Healthy system with good coverage and no fallback/silent issues passes."""
    report = assess_metastability(
        subsystem="test_healthy",
        coverage_hot_paths=0.95,
        single_point_dependencies=0,
        untested_fallbacks=0,
        config_implicit=False,
        silent_failure_history=0,
    )

    assert report.fragile_stable_state is False
    assert report.hidden_dependency_score == 0.0
    assert report.confidence_penalty == 0.0
    assert report.perturbation_needed is False
    assert not report.reasons


def test_monoculture_detected() -> None:
    """Subsystem with SPOFs and implicit config triggers fragility signal."""
    report = assess_metastability(
        subsystem="test_spof",
        coverage_hot_paths=1.0,  # Great coverage
        single_point_dependencies=2,  # 0.20
        config_implicit=True,  # 0.15
        silent_failure_history=1,  # 0.15
    )

    # 0.20 + 0.15 + 0.15 = 0.50 >= 0.45 threshold
    assert report.fragile_stable_state is True
    assert report.hidden_dependency_score == 0.50
    assert len(report.reasons) == 3


def test_silent_failure_history() -> None:
    """Historical silent failures add to fragility but may not trigger alone."""
    report = assess_metastability(
        subsystem="test_silent",
        coverage_hot_paths=1.0,
        silent_failure_history=1,  # +0.15
    )

    assert report.fragile_stable_state is False
    assert report.hidden_dependency_score == 0.15
    assert "1 historical silent failure" in report.reasons[0]


def test_block_on_many_signals() -> None:
    """System with many issues receives maximal penalty."""
    report = assess_metastability(
        subsystem="test_critical",
        coverage_hot_paths=0.1,  # 0.30
        single_point_dependencies=5,  # 0.20
        untested_fallbacks=3,  # 0.20
        config_implicit=True,  # 0.15
        silent_failure_history=2,  # 0.15
    )

    assert report.fragile_stable_state is True
    assert report.hidden_dependency_score == 1.00
    assert report.confidence_penalty == 0.2
    assert len(report.reasons) == 5


def test_metastability_property_bounds_capped() -> None:
    """Property: The hidden_dependency_score is strictly capped at 1.0."""
    report = assess_metastability(
        subsystem="test_capped",
        coverage_hot_paths=0.0,  # 0.30
        single_point_dependencies=100,  # 0.20
        untested_fallbacks=100,  # 0.20
        config_implicit=True,  # 0.15
        silent_failure_history=100,  # 0.15
    )

    assert report.fragile_stable_state is True
    assert report.hidden_dependency_score == 1.00  # Maxed out, not exceeding 1.0
    assert report.confidence_penalty == 0.2


def test_metastability_property_monotonic_bad_signals() -> None:
    """Property: Increasing bad signals strictly does not decrease the score."""
    base_report = assess_metastability(
        subsystem="test_monotonic",
        coverage_hot_paths=0.5,
    )
    
    worse_report_1 = assess_metastability(
        subsystem="test_monotonic",
        coverage_hot_paths=0.5,
        single_point_dependencies=2,
    )
    
    worse_report_2 = assess_metastability(
        subsystem="test_monotonic",
        coverage_hot_paths=0.5,
        single_point_dependencies=2,
        silent_failure_history=1,
    )

    assert worse_report_1.hidden_dependency_score >= base_report.hidden_dependency_score
    assert worse_report_2.hidden_dependency_score >= worse_report_1.hidden_dependency_score


def test_metastability_property_idempotency() -> None:
    """Property: Identical inputs yield identical outputs (purity)."""
    kwargs = {
        "subsystem": "test_pure",
        "coverage_hot_paths": 0.5,
        "single_point_dependencies": 2,
    }
    
    report1 = assess_metastability(**kwargs)
    report2 = assess_metastability(**kwargs)

    assert report1.fragile_stable_state == report2.fragile_stable_state
    assert report1.hidden_dependency_score == report2.hidden_dependency_score
    assert report1.confidence_penalty == report2.confidence_penalty
    assert set(report1.reasons) == set(report2.reasons)
