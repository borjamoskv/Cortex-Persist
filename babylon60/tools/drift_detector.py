import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np


@dataclass
class BehavioralSnapshot:
    model_id: str
    timestamp_iso: str
    state_vectors: np.ndarray  # Shape: (n_samples, d_dimensions)
    metadata: dict[str, Any] = field(default_factory=dict)
    sha256_hash: str = ""

    def __post_init__(self):
        if not self.sha256_hash and self.state_vectors is not None:
            # Deterministic hash generation from state vectors bytes
            h = hashlib.sha256(self.state_vectors.tobytes())
            self.sha256_hash = h.hexdigest()


@dataclass
class DriftResult:
    kl_forward: float
    kl_reverse: float
    symmetric_kl: float
    per_dimension_contribution: np.ndarray
    is_significant: bool
    confidence_level: str


@dataclass
class SilentUpdateAlert:
    detected: bool
    severity: str
    kl_value: float
    drift_dimensions: list[int]
    recommended_action: str


class DriftDetector:
    def __init__(self, regularization_eps: float = 1e-5):
        self.regularization_eps = regularization_eps

    def capture_snapshot(
        self, model_id: str, states: list[np.ndarray], metadata: Optional[dict[str, Any]] = None
    ) -> BehavioralSnapshot:
        if not states:
            raise ValueError("State vector list is empty")

        matrix = np.array(states)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)

        timestamp = datetime.now(timezone.utc).isoformat()
        return BehavioralSnapshot(
            model_id=model_id,
            timestamp_iso=timestamp,
            state_vectors=matrix,
            metadata=metadata or {},
        )

    def _estimate_gaussian_params(self, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Estimates Mean and Covariance with additive Laplace regularization (Σ_reg = Σ + εI).
        Ensures robust divergence computation under disjoint, partial, or degenerate supports.
        """
        n, d = matrix.shape
        mean = np.mean(matrix, axis=0)

        if n < 2:
            # Fallback for insufficient sample size
            cov = np.eye(d) * self.regularization_eps
            return mean, cov

        cov = np.cov(matrix, rowvar=False)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])

        # Regularization: Σ_reg = Σ + εI
        cov = cov + np.eye(d) * self.regularization_eps
        return mean, cov

    def compute_kl_divergence(
        self, snapshot_a: BehavioralSnapshot, snapshot_b: BehavioralSnapshot
    ) -> DriftResult:
        """
        Computes forward KL(B || A) and reverse KL(A || B) using smoothed Gaussian approximation.
        Applies additive smoothing to guarantee compatible support across observed latent densities.
        Assumes snapshot_a is baseline (N0) and snapshot_b is target/current (N1).
        Formula:
        KL(N1 || N0) = 0.5 * [tr(S0^-1 S1) + (mu0 - mu1)^T S0^-1 (mu0 - mu1) - d + ln(det(S0)/det(S1))]
        """
        v_a = snapshot_a.state_vectors
        v_b = snapshot_b.state_vectors

        if v_a.shape[1] != v_b.shape[1]:
            raise ValueError(
                f"Dimension mismatch between state vectors: baseline={v_a.shape[1]}, current={v_b.shape[1]}"
            )

        d = v_a.shape[1]

        mu_a, cov_a = self._estimate_gaussian_params(v_a)
        mu_b, cov_b = self._estimate_gaussian_params(v_b)

        # Precompute inverses and determinants
        try:
            inv_cov_a = np.linalg.pinv(cov_a)
            inv_cov_b = np.linalg.pinv(cov_b)

            sign_a, logdet_a = np.linalg.slogdet(cov_a)
            sign_b, logdet_b = np.linalg.slogdet(cov_b)

            det_term = logdet_a - logdet_b
        except Exception:
            # Safe recovery back to Euclidean boundaries
            inv_cov_a = np.eye(d)
            inv_cov_b = np.eye(d)
            det_term = 0.0

        # Forward: KL(B || A) -> current relative to baseline
        diff = mu_a - mu_b
        tr_term_f = np.trace(inv_cov_a @ cov_b)
        quad_term_f = np.dot(np.dot(diff, inv_cov_a), diff)
        kl_forward = float(0.5 * (tr_term_f + quad_term_f - d + det_term))
        kl_forward = max(kl_forward, 0.0)

        # Reverse: KL(A || B) -> baseline relative to current
        tr_term_r = np.trace(inv_cov_b @ cov_a)
        quad_term_r = np.dot(np.dot(diff, inv_cov_b), diff)
        kl_reverse = float(0.5 * (tr_term_r + quad_term_r - d - det_term))
        kl_reverse = max(kl_reverse, 0.0)

        symmetric_kl = 0.5 * (kl_forward + kl_reverse)

        # Per-dimension contribution estimation using diagonal variance ratio + mean delta
        var_a = np.diag(cov_a)
        var_b = np.diag(cov_b)
        per_dim = []
        for i in range(d):
            # 1D KL divergence formulation per axis
            term_1d = 0.5 * (
                var_b[i] / var_a[i]
                + (mu_a[i] - mu_b[i]) ** 2 / var_a[i]
                - 1.0
                + math.log(var_a[i] / var_b[i])
            )
            per_dim.append(max(float(term_1d), 0.0))

        per_dim_arr = np.array(per_dim)

        # Significance classification
        is_sig = symmetric_kl > 1.5

        # Confidence score based on sample sizes
        n_a = v_a.shape[0]
        n_b = v_b.shape[0]
        min_n = min(n_a, n_b)
        if min_n > 50:
            confidence = "C5"
        elif min_n > 20:
            confidence = "C4"
        elif min_n > 10:
            confidence = "C3"
        elif min_n > 5:
            confidence = "C2"
        else:
            confidence = "C1"

        return DriftResult(
            kl_forward=kl_forward,
            kl_reverse=kl_reverse,
            symmetric_kl=symmetric_kl,
            per_dimension_contribution=per_dim_arr,
            is_significant=is_sig,
            confidence_level=confidence,
        )

    def compute_symmetric_kl(
        self, snapshot_a: BehavioralSnapshot, snapshot_b: BehavioralSnapshot
    ) -> float:
        res = self.compute_kl_divergence(snapshot_a, snapshot_b)
        return res.symmetric_kl

    def detect_silent_update(
        self, baseline: BehavioralSnapshot, current: BehavioralSnapshot, threshold: float = 2.0
    ) -> SilentUpdateAlert:
        res = self.compute_kl_divergence(baseline, current)

        # Top 3 drifting dimensions
        drift_dims = []
        if len(res.per_dimension_contribution) > 0:
            sorted_indices = np.argsort(res.per_dimension_contribution)[::-1]
            drift_dims = [
                int(idx) for idx in sorted_indices[:3] if res.per_dimension_contribution[idx] > 0.1
            ]

        detected = res.symmetric_kl >= threshold

        if not detected:
            severity = "none"
            recommended = "No action required. Endpoints match operational signature."
        elif res.symmetric_kl < threshold * 2:
            severity = "medium"
            recommended = "Warn client services. Behavioral variance detected but within tolerance."
        elif res.symmetric_kl < threshold * 5:
            severity = "high"
            recommended = "Flag silent update. Prompt structures may require adaptation."
        else:
            severity = "critical"
            recommended = (
                "Immediate rollback advised. Observable behavior has diverged significantly."
            )

        return SilentUpdateAlert(
            detected=detected,
            severity=severity,
            kl_value=res.symmetric_kl,
            drift_dimensions=drift_dims,
            recommended_action=recommended,
        )
