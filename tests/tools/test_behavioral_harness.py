import math
import numpy as np
import pytest

from babylon60.tools.system_identifier import (
    SystemIdentifier,
    MahalanobisDistanceCalculator,
    BehavioralStateVector,
)
from babylon60.tools.drift_detector import DriftDetector, BehavioralSnapshot
from babylon60.tools.coverage_entropy import (
    CoverageAnalyzer,
    MutualInformationEstimator,
    ExcitationFamily,
)
from babylon60.tools.excitation_batteries import BatteryManager, DifficultyLevel
from babylon60.tools.behavioral_harness import BehavioralHarness, BehavioralProfile


def test_mahalanobis_vs_euclidean():
    # Setup calibration data such that the sample covariance matrix converges to Identity matrix
    # Mahalanobis distance with covariance = Identity equals Euclidean distance
    dim = 5
    n_samples = 1000
    calibration_data = np.random.normal(0, 1.0, size=(n_samples, dim))

    calculator = MahalanobisDistanceCalculator(calibration_data)

    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([1.1, 1.9, 3.0, 4.0, 5.1])

    d_m = calculator.distance(a, b)
    d_e = np.linalg.norm(a - b)

    # Assert they are extremely close (almost equal due to sample cov ≈ I)
    assert abs(d_m - d_e) < 0.1


def test_coverage_entropy_uniform():
    analyzer = CoverageAnalyzer()

    # Setup uniform variance across 4 orthogonal dimensions
    # D = 4, H_cov should be log2(4) = 2.0
    dim = 4
    n_samples = 100

    # Generate vectors where each component has exactly the same variance
    # Component 0 has std=1, Component 1 has std=1, etc.
    vectors = np.random.normal(0, 1.0, size=(n_samples, dim))

    # Force exact sample variance on each column
    for d in range(dim):
        vectors[:, d] = (vectors[:, d] - np.mean(vectors[:, d])) / np.std(vectors[:, d])

    h_cov = analyzer.compute_coverage_entropy(vectors)

    assert abs(h_cov - math.log2(dim)) < 0.05


def test_coverage_entropy_concentrated():
    analyzer = CoverageAnalyzer()

    dim = 4
    n_samples = 100
    # Generate vectors where column 0 has high variance and all others have near zero variance
    vectors = np.zeros((n_samples, dim))
    vectors[:, 0] = np.random.normal(0, 10.0, size=n_samples)
    vectors[:, 1:] = np.random.normal(0, 1e-6, size=(n_samples, dim - 1))

    h_cov = analyzer.compute_coverage_entropy(vectors)

    # High concentration should yield H_cov near 0
    assert h_cov < 0.1


def test_dtw_identical_trajectories():
    sys_id = SystemIdentifier()

    # Create identical trajectories
    dim = 32
    traj_a = []
    for i in range(5):
        embedding = np.random.normal(0, 1.0, size=dim)
        traj_a.append(
            BehavioralStateVector(
                turn_index=i,
                response_length=100,
                lexical_entropy=4.2,
                sim_to_context=0.8,
                itl_ms=15.0,
                refusal_detected=False,
                embedding_vector=embedding,
            )
        )

    dtw_dist = sys_id.compute_trajectory_dtw(traj_a, traj_a)
    dtw_norm = sys_id.compute_trajectory_dtw_normalized(traj_a, traj_a)

    assert dtw_dist == pytest.approx(0.0, abs=1e-9)
    assert dtw_norm == pytest.approx(0.0, abs=1e-9)


def test_dtw_different_trajectories():
    sys_id = SystemIdentifier()

    # Two trajectories varying significantly
    dim = 32
    traj_a = []
    traj_b = []
    for i in range(5):
        emb_a = np.ones(dim) * 0.1
        emb_b = np.ones(dim) * 0.9

        traj_a.append(
            BehavioralStateVector(
                turn_index=i,
                response_length=100,
                lexical_entropy=4.2,
                sim_to_context=0.8,
                itl_ms=15.0,
                refusal_detected=False,
                embedding_vector=emb_a,
            )
        )

        traj_b.append(
            BehavioralStateVector(
                turn_index=i,
                response_length=2000,
                lexical_entropy=1.2,
                sim_to_context=0.2,
                itl_ms=150.0,
                refusal_detected=True,
                embedding_vector=emb_b,
            )
        )

    dtw_dist = sys_id.compute_trajectory_dtw(traj_a, traj_b)
    dtw_norm = sys_id.compute_trajectory_dtw_normalized(traj_a, traj_b)

    assert dtw_dist > 0.0
    assert dtw_norm > 0.0


def test_kl_identical_gaussians():
    detector = DriftDetector()

    # Create identical distributions
    n_samples = 100
    dim = 4
    data = np.random.normal(5.0, 2.0, size=(n_samples, dim))

    snap_a = BehavioralSnapshot(model_id="baseline", timestamp_iso="now", state_vectors=data)
    snap_b = BehavioralSnapshot(model_id="current", timestamp_iso="now", state_vectors=data)

    res = detector.compute_kl_divergence(snap_a, snap_b)

    # Identical should mean KL divergence ≈ 0
    assert res.kl_forward < 0.1
    assert res.kl_reverse < 0.1
    assert res.symmetric_kl < 0.1
    assert not res.is_significant


def test_kl_different_gaussians():
    detector = DriftDetector()

    # Two distinct distributions (baseline N(0, I) vs N(3, I))
    n_samples = 100
    dim = 4
    data_a = np.random.normal(0.0, 1.0, size=(n_samples, dim))
    data_b = np.random.normal(3.0, 1.0, size=(n_samples, dim))

    snap_a = BehavioralSnapshot(model_id="baseline", timestamp_iso="now", state_vectors=data_a)
    snap_b = BehavioralSnapshot(model_id="current", timestamp_iso="now", state_vectors=data_b)

    res = detector.compute_kl_divergence(snap_a, snap_b)

    # Diverging distributions should yield a large KL value
    assert res.symmetric_kl > 5.0
    assert res.is_significant


def test_battery_hash_consistency():
    mgr1 = BatteryManager()
    mgr2 = BatteryManager()

    h1 = mgr1.get_battery_hash()
    h2 = mgr2.get_battery_hash()

    # Assert battery hashes are fully deterministic and match across instantiations
    assert h1 == h2
    assert len(h1) == 64


def test_mutual_information():
    estimator = MutualInformationEstimator()

    # Fully correlated signals should yield high MI
    x = np.linspace(0, 10, 100)
    y = x + np.random.normal(0, 0.01, 100)

    mi_high = estimator.estimate_mi(x, y, bins=10)

    # Uncorrelated signals should yield low MI
    x_rand = np.random.normal(0, 1.0, 100)
    y_rand = np.random.normal(0, 1.0, 100)

    mi_low = estimator.estimate_mi(x_rand, y_rand, bins=10)

    assert mi_high > mi_low
