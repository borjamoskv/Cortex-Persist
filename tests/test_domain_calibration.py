"""CORTEX v8.0 — Domain-Specific Calibration Tests.

Verifies that Brier Score segmentation by project_id correctly identifies
overconfident/underconfident states in specific domains.
"""

import pytest

from cortex.memory.metamemory import MetamemoryMonitor, RetrievalOutcome


def test_segmented_brier_drift():
    """Verify that different projects can have different calibration levels."""
    monitor = MetamemoryMonitor()

    # Project A (Technical): Well-calibrated
    # 10 samples, 80% confidence, 8 success (Perfectly calibrated)
    for _ in range(10):
        monitor.record_outcome(
            RetrievalOutcome(
                query="rust safety",
                project_id="technical",
                predicted_confidence=0.8,
                actual_success=True,
            )
        )
    for _ in range(2):
        monitor.record_outcome(
            RetrievalOutcome(
                query="rust safety",
                project_id="technical",
                predicted_confidence=0.8,
                actual_success=False,
            )
        )

    # Project B (Financial): Overconfident (Lying)
    # 10 samples, 95% confidence, only 2 success
    for _ in range(2):
        monitor.record_outcome(
            RetrievalOutcome(
                query="btc price prediction",
                project_id="financial",
                predicted_confidence=0.95,
                actual_success=True,
            )
        )
    for _ in range(8):
        monitor.record_outcome(
            RetrievalOutcome(
                query="btc price prediction",
                project_id="financial",
                predicted_confidence=0.95,
                actual_success=False,
            )
        )

    # 1. Check Technical Score (should be low/good)
    tech_brier = monitor.calibration_score(project_id="technical")
    # (1.0-0.8)^2 = 0.04 * 10 = 0.4
    # (0.0-0.8)^2 = 0.64 * 2  = 1.28
    # Total = 1.68 / 12 = 0.14 (Fair/Good)
    assert 0.1 < tech_brier < 0.2

    # 2. Check Financial Score (should be high/poor)
    fin_brier = monitor.calibration_score(project_id="financial")
    # (1.0-0.95)^2 = 0.0025 * 2 = 0.005
    # (0.0-0.95)^2 = 0.9025 * 8 = 7.22
    # Total = 7.225 / 10 = 0.7225 (Very Poor - Miente!)
    assert fin_brier > 0.6

    # 3. Check Global Score
    global_brier = monitor.calibration_score()
    # Average of both domains
    assert 0.14 < global_brier < 0.72

    # 4. Check Report
    report = monitor.calibration_report()
    assert report["segmented_brier"]["technical"] == pytest.approx(tech_brier, abs=1e-4)
    assert report["segmented_brier"]["financial"] == pytest.approx(fin_brier, abs=1e-4)
    assert "technical" in report["active_domains"]
    assert "financial" in report["active_domains"]


def test_insufficient_data_per_project():
    """A project with few samples should report -1.0 even if global data is sufficient."""
    monitor = MetamemoryMonitor()

    # 20 samples for project A
    for _ in range(20):
        monitor.record_outcome(
            RetrievalOutcome(
                query="a", project_id="A", predicted_confidence=0.5, actual_success=True
            )
        )

    # Only 2 samples for project B
    for _ in range(2):
        monitor.record_outcome(
            RetrievalOutcome(
                query="b", project_id="B", predicted_confidence=0.5, actual_success=True
            )
        )

    assert monitor.calibration_score(project_id="A") >= 0
    assert monitor.calibration_score(project_id="B") == -1.0

    report = monitor.calibration_report()
    assert report["segmented_brier"]["B"] == -1.0
    assert "B" not in report["active_domains"]
    assert "A" in report["active_domains"]
