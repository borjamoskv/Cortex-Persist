# [C5-REAL] Exergy-Maximized
import pytest
from cortex.runtime.replay.controller import (
    TemporalConsistencyController,
    EntropyViolation,
    AttractorViolation,
)


def test_entropy_clamp_stable():
    # Estable (sin crecimiento)
    trajectory = [
        {"version": 0, "state_hash": "h0", "data": {"a": 1}},
        {"version": 1, "state_hash": "h1", "data": {"a": 1}},
        {"version": 2, "state_hash": "h2", "data": {"a": 1}},
    ]
    controller = TemporalConsistencyController().clamp_entropy(0.5)
    report = controller.regulate(trajectory)
    assert report is not None


def test_entropy_clamp_violation():
    # Complejidad crece muy rápido (1, 3, 6 keys)
    trajectory = [
        {"version": 0, "state_hash": "h0", "data": {"k1": 1}},
        {"version": 1, "state_hash": "h1", "data": {"k1": 1, "k2": 2, "k3": 3}},
        {
            "version": 2,
            "state_hash": "h2",
            "data": {"k1": 1, "k2": 2, "k3": 3, "k4": 4, "k5": 5, "k6": 6},
        },
    ]
    # mean gradient será ~2.5
    controller = TemporalConsistencyController().clamp_entropy(1.0)

    with pytest.raises(EntropyViolation):
        controller.regulate(trajectory)


def test_attractor_strict_determinism():
    baseline = [
        {"version": 0, "data": {"hash": "h0"}, "state_hash": "h0"},
        {"version": 1, "data": {"hash": "h1"}, "state_hash": "h1"},
    ]

    # Exact match
    controller = TemporalConsistencyController(baseline).enforce_strict_determinism()
    controller.regulate(baseline)

    # Divergent
    divergent = [
        {"version": 0, "data": {"hash": "h0"}, "state_hash": "h0"},
        {"version": 1, "data": {"hash": "h1_mod"}, "state_hash": "h1_mod"},
    ]

    with pytest.raises(AttractorViolation):
        controller.regulate(divergent)


def test_attractor_tolerance():
    baseline = [
        {"version": 0, "state_hash": "h0", "data": {"k1": 1}},
        {"version": 1, "state_hash": "h1", "data": {"k1": 1, "k2": 2}},
    ]

    # Slightly divergent (1 out of 2 keys changed = 0.5 value diff ratio, composit ~ 0.5)
    divergent = [
        {"version": 0, "state_hash": "h0", "data": {"k1": 1}},
        {"version": 1, "state_hash": "h1_mod", "data": {"k1": 1, "k2": 99}},  # k2 differs
    ]

    controller = TemporalConsistencyController(baseline).enforce_attractor(0.6)
    # Should pass because 0.35 < 0.6
    report = controller.regulate(divergent)
    assert report.max_distance > 0.0

    # If we lower tolerance to 0.3, it should fail
    strict_controller = TemporalConsistencyController(baseline).enforce_attractor(0.3)
    with pytest.raises(AttractorViolation):
        strict_controller.regulate(divergent)
