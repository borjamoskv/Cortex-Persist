# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import Mock

from babylon60.runtime.divergence import ExecutionDiff, Trace, DivergenceEngine
from babylon60.runtime.homeostasis import HomeostaticController, DriftThresholds


@pytest.fixture
def divergence_engine_mock():
    return Mock(spec=DivergenceEngine)


@pytest.fixture
def controller(divergence_engine_mock):
    return HomeostaticController(divergence_engine=divergence_engine_mock)


def test_shadow_mode_expected_drift(controller, divergence_engine_mock):
    """
    Validates that a shift within EXPECTED_DRIFT_MAX is correctly categorized
    as EXPECTED_DRIFT and does not flag for action.
    """
    diff = ExecutionDiff(
        tick=10,
        state_drift={"a": 1, "b": 2},
        event_delta={},
        semantic_shift=0.2,  # < 0.3
        entropy_gradient=0.1,
    )
    divergence_engine_mock.diff.return_value = diff

    metrics = controller.monitor_and_detect(Mock(spec=Trace), Mock(spec=Trace))

    assert metrics.tick == 10
    assert metrics.semantic_shift == 0.2
    assert metrics.drift_category == "EXPECTED_DRIFT"
    assert not metrics.requires_action


def test_shadow_mode_pathological_drift(controller, divergence_engine_mock):
    """
    Validates that a shift above PATHOLOGICAL_DRIFT_MIN is correctly categorized
    as PATHOLOGICAL_DRIFT and flags for action.
    """
    diff = ExecutionDiff(
        tick=42,
        state_drift={"a": 1, "b": 9},
        event_delta={},
        semantic_shift=0.8,  # > 0.7
        entropy_gradient=0.9,
    )
    divergence_engine_mock.diff.return_value = diff

    metrics = controller.monitor_and_detect(Mock(spec=Trace), Mock(spec=Trace))

    assert metrics.drift_category == "PATHOLOGICAL_DRIFT"
    assert metrics.requires_action


def test_shadow_mode_warning_drift_low_entropy(controller, divergence_engine_mock):
    """
    Validates the transition zone. Shift between 0.3 and 0.7 with low entropy
    should not flag for action.
    """
    diff = ExecutionDiff(
        tick=100,
        state_drift={"x": "val1", "y": "val2"},
        event_delta={},
        semantic_shift=0.5,
        entropy_gradient=0.4,  # < 0.8
    )
    divergence_engine_mock.diff.return_value = diff

    metrics = controller.monitor_and_detect(Mock(spec=Trace), Mock(spec=Trace))

    assert metrics.drift_category == "WARNING_DRIFT"
    assert not metrics.requires_action


def test_shadow_mode_warning_drift_high_entropy(controller, divergence_engine_mock):
    """
    Validates the transition zone. Shift between 0.3 and 0.7 with high entropy
    should flag for preventative action.
    """
    diff = ExecutionDiff(
        tick=100,
        state_drift={"x": "val1", "y": "val2"},
        event_delta={},
        semantic_shift=0.5,
        entropy_gradient=0.85,  # > 0.8
    )
    divergence_engine_mock.diff.return_value = diff

    metrics = controller.monitor_and_detect(Mock(spec=Trace), Mock(spec=Trace))

    assert metrics.drift_category == "WARNING_DRIFT"
    assert metrics.requires_action


def test_shadow_mode_remediate_bypassed(controller):
    """
    Ensures that remediate() does not execute in SHADOW mode.
    """
    # Since remediate just returns in SHADOW mode, we expect no exception.
    metrics = Mock()
    controller.remediate(metrics)  # Should return silently

    # If mode is changed, it should raise NotImplementedError
    controller.mode = "ACTIVE"
    with pytest.raises(NotImplementedError):
        controller.remediate(metrics)
