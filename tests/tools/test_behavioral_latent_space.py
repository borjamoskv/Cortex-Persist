import numpy as np
import pytest
from babylon60.tools.system_identifier import SystemIdentifier, ConversationalState
from babylon60.tools.drift_detector import DriftDetector, BehavioralSnapshot, DriftResult, SilentUpdateAlert

def test_system_identifier_extract_state():
    sys_id = SystemIdentifier()
    
    # 1. State extraction for regular response
    state1 = sys_id.extract_state(
        turn_idx=1,
        response="This is a simple normal conversational response from the model.",
        prev_response=None,
        itl=120.0
    )
    
    assert isinstance(state1, ConversationalState)
    assert state1.turn_index == 1
    assert state1.response_length > 0
    assert state1.lexical_entropy > 0.0
    assert state1.sim_to_context == 1.0
    assert state1.itl_ms == 120.0
    assert not state1.refusal_detected
    assert state1.embedding_vector.shape == (8,)

    # 2. State extraction with previous state (cosine similarity)
    state2 = sys_id.extract_state(
        turn_idx=2,
        response="This is another conversational response.",
        prev_response="This is a simple normal conversational response from the model.",
        itl=150.0
    )
    
    assert state2.turn_index == 2
    assert 0.0 <= state2.sim_to_context <= 1.0
    assert not state2.refusal_detected

    # 3. State extraction with refusal detection
    state_refusal = sys_id.extract_state(
        turn_idx=3,
        response="I am sorry, but I cannot fulfill this request as an AI assistant.",
        prev_response=None,
        itl=80.0
    )
    assert state_refusal.refusal_detected


def test_system_identifier_behavioral_coverage():
    sys_id = SystemIdentifier()
    
    # High variance matrix (diverse behaviors)
    matrix_high_var = np.array([
        [1.0, 0.1, 0.5],
        [2.0, 10.0, 0.6],
        [1.5, 5.0, 0.1],
        [3.0, 0.2, 0.9]
    ])
    cov_high = sys_id.compute_behavioral_coverage(matrix_high_var)
    assert cov_high > 0.0

    # Low variance matrix (uniform behaviors)
    matrix_low_var = np.array([
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
    ])
    cov_low = sys_id.compute_behavioral_coverage(matrix_low_var)
    assert cov_low == 0.0

    # Empty matrix check
    assert sys_id.compute_behavioral_coverage(np.array([[]])) == 0.0


def test_system_identifier_trajectory_dtw():
    sys_id = SystemIdentifier()
    
    # Trajectory A
    traj_a = [
        ConversationalState(1, 100, 3.5, 0.9, 100.0, False, np.ones(32)),
        ConversationalState(2, 200, 4.2, 0.8, 150.0, False, np.ones(32) * 0.8)
    ]
    
    # Trajectory B (similar)
    traj_b = [
        ConversationalState(1, 110, 3.4, 0.9, 110.0, False, np.ones(32)),
        ConversationalState(2, 190, 4.3, 0.7, 140.0, False, np.ones(32) * 0.8)
    ]

    dtw_dist = sys_id.compute_trajectory_dtw(traj_a, traj_b)
    assert dtw_dist >= 0.0
    assert dtw_dist != float("inf")

    # Empty trajectory corner case
    assert sys_id.compute_trajectory_dtw([], traj_b) == float("inf")


def test_system_identifier_profile_temperament():
    sys_id = SystemIdentifier()
    
    states = [
        ConversationalState(1, 500, 4.5, 0.9, 100.0, False, np.zeros(32)),
        ConversationalState(2, 800, 4.8, 0.8, 120.0, False, np.zeros(32)),
        ConversationalState(3, 1200, 5.2, 0.75, 150.0, False, np.zeros(32)),
    ]
    
    profile = sys_id.profile_temperament(states)
    assert "conservator_exploratory" in profile
    assert "stable_adaptable" in profile
    assert "literal_inferential" in profile
    assert "compact_expansive" in profile
    
    for val in profile.values():
        assert 0.0 <= val <= 1.0

    # Empty list fallback
    empty_profile = sys_id.profile_temperament([])
    assert empty_profile == {
        "conservator_exploratory": 0.5,
        "stable_adaptable": 0.5,
        "literal_inferential": 0.5,
        "compact_expansive": 0.5
    }


def test_drift_detector_snapshots_and_fit():
    detector = DriftDetector(eps=1e-5)
    
    states_a = np.random.normal(0, 1, (10, 5))
    states_b = np.random.normal(0.5, 1, (12, 5))
    
    snap_a = detector.capture_snapshot("model_a", states_a, {"version": "1.0"})
    snap_b = detector.capture_snapshot("model_a", states_b, {"version": "1.1"})
    
    assert isinstance(snap_a, BehavioralSnapshot)
    assert snap_a.model_id == "model_a"
    assert snap_a.sha256_hash is not None
    assert snap_a.metadata == {"version": "1.0"}
    assert snap_a.state_vectors.shape == (10, 5)

    # Check fit gaussian
    mu_a, sigma_a = detector._fit_gaussian(states_a)
    assert mu_a.shape == (5,)
    assert sigma_a.shape == (5, 5)
    # Check regularized diagonal addition
    assert np.all(np.diag(sigma_a) >= 1e-5)


def test_drift_detector_kl_divergence():
    detector = DriftDetector(eps=1e-6)
    
    # 1. Identical distributions (KL should be close to 0)
    states_ref = np.random.normal(0, 1, (100, 3))
    snap_ref1 = detector.capture_snapshot("ref", states_ref)
    snap_ref2 = detector.capture_snapshot("ref", states_ref)
    
    result_same = detector.compute_kl_divergence(snap_ref1, snap_ref2)
    assert isinstance(result_same, DriftResult)
    assert result_same.symmetric_kl < 0.01
    assert not result_same.is_significant

    # 2. Shifted distributions
    states_shifted = np.random.normal(3.0, 1, (100, 3))
    snap_shifted = detector.capture_snapshot("shifted", states_shifted)
    
    result_drift = detector.compute_kl_divergence(snap_ref1, snap_shifted)
    assert result_drift.symmetric_kl > 1.0
    assert result_drift.is_significant
    assert len(result_drift.per_dimension_contribution) == 3


def test_drift_detector_alerting():
    detector = DriftDetector(eps=1e-6)
    
    states_ref = np.random.normal(0, 1, (100, 3))
    states_drift = np.random.normal(10.0, 1, (100, 3))
    
    snap_ref = detector.capture_snapshot("model_x", states_ref)
    snap_drift = detector.capture_snapshot("model_x", states_drift)
    
    alert = detector.detect_silent_update(snap_ref, snap_drift, threshold=2.0)
    assert isinstance(alert, SilentUpdateAlert)
    assert alert.detected
    assert alert.kl_value > 2.0
    assert alert.severity in ("medium", "high", "critical")
    assert alert.recommended_action != "no_action"
