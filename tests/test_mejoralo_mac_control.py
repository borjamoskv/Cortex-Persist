"""Tests for MEJORAlo macOS system telemetry integration."""

import sys
from unittest.mock import patch

from cortex.extensions.mejoralo.constants import (
    MAC_AX_PENALTY,
    MAC_PROCESS_ENTROPY_LIMIT,
    MAC_PROCESS_PENALTY_PER_10,
)
from cortex.extensions.mejoralo.mac_control import (
    mac_control_dimension_kwargs,
    mac_system_snapshot,
    score_mac_control,
)
from cortex.extensions.mejoralo.models import MacSnapshot


def test_mac_snapshot_structure():
    """Verify MacSnapshot is well-formed regardless of platform."""
    snap = mac_system_snapshot()
    assert isinstance(snap, MacSnapshot)
    if sys.platform != "darwin":
        assert snap.platform == "unsupported"
        assert snap.cpu_percent == 0.0
    else:
        assert snap.platform == "darwin"
        assert isinstance(snap.cpu_percent, float)
        assert isinstance(snap.memory_pressure, str)
        assert isinstance(snap.process_count, int)
        assert isinstance(snap.ax_trusted, bool)
        assert isinstance(snap.gpu_active, bool)
        assert isinstance(snap.thermal_state, str)
        assert isinstance(snap.timestamp, str)


def test_score_mac_control_perfect():
    """Verify nominal state returns 100 with no findings."""
    snap = MacSnapshot(
        platform="darwin",
        cpu_percent=10.0,
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=150,
        ax_trusted=True,
        gpu_active=True,
        timestamp="2026-03-17T00:00:00Z",
    )
    score, findings = score_mac_control(snap)
    assert score == 100
    assert not findings


def test_score_mac_control_ax_penalty():
    """Verify missing AX trust penalizes score."""
    snap = MacSnapshot(
        platform="darwin",
        cpu_percent=10.0,
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=150,
        ax_trusted=False,  # NOT TRUSTED
        gpu_active=True,
        timestamp="2026-03-17T00:00:00Z",
    )
    score, findings = score_mac_control(snap)
    assert score == 100 - MAC_AX_PENALTY
    assert len(findings) == 1
    assert "AX trust not granted" in findings[0]


def test_score_mac_control_process_entropy():
    """Verify process limit triggers penalty."""
    over_limit = MAC_PROCESS_ENTROPY_LIMIT + 35  # +35 = 3 blocks of 10
    snap = MacSnapshot(
        platform="darwin",
        cpu_percent=10.0,
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=over_limit,
        ax_trusted=True,
        gpu_active=True,
        timestamp="2026-03-17T00:00:00Z",
    )
    score, findings = score_mac_control(snap)
    expected_penalty = 3 * MAC_PROCESS_PENALTY_PER_10
    assert score == 100 - expected_penalty
    assert len(findings) == 1
    assert "Process entropy high" in findings[0]


def test_score_mac_control_thermal_warn():
    """Verify serious thermal state imposes correct penalty."""
    snap = MacSnapshot(
        platform="darwin",
        cpu_percent=50.0,
        memory_pressure="ok",
        thermal_state="Serious",
        process_count=100,
        ax_trusted=True,
        gpu_active=True,
        timestamp="2026-03-17T00:00:00Z",
    )
    score, findings = score_mac_control(snap)
    assert score == 75  # 100 - 25
    assert len(findings) == 1
    assert "Serious thermal state" in findings[0]


def test_mac_sys_platform_guard():
    """Verify unsupported platform returns -1 and no findings."""
    snap = MacSnapshot(
        platform="unsupported",
        cpu_percent=0.0,
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=0,
        ax_trusted=False,
        gpu_active=False,
        timestamp="2026-03-17T00:00:00Z",
    )
    score, findings = score_mac_control(snap)
    assert score == -1
    assert not findings


@patch("sys.platform", "darwin")
@patch("cortex.extensions.mejoralo.mac_control.mac_system_snapshot")
def test_mac_control_dimension_kwargs(mock_snapshot):
    """Verify kwargs builder returns neutral score on unsupported, real score on darwin."""
    mock_snapshot.return_value = MacSnapshot(
        platform="darwin",
        cpu_percent=95.0,  # +5% over 90% -> penalty logic applies
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=100,
        ax_trusted=True,
        gpu_active=True,
        timestamp="2026-03-17T00:00:00Z",
    )
    kwargs = mac_control_dimension_kwargs()
    assert kwargs["name"] == "Control macOS"
    assert kwargs["weight"] == "medium"
    assert kwargs["score"] < 100  # CPU penalty applied
    assert len(kwargs["findings"]) == 1

    # Test unsupported fallback
    mock_snapshot.return_value = MacSnapshot(
        platform="unsupported",
        cpu_percent=0.0,
        memory_pressure="ok",
        thermal_state="Nominal",
        process_count=0,
        ax_trusted=False,
        gpu_active=False,
        timestamp="2026-03-17T00:00:00Z",
    )
    kwargs_unsupported = mac_control_dimension_kwargs()
    assert kwargs_unsupported["score"] == 100  # -1 is masked to 100 neutral
