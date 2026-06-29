"""Coverage Entropy & Mutual Information — numpy-only implementation.

H_cov(U) = -sum(p_d * log2(p_d)) where p_d = variance proportion per dimension.

Author: borjamoskv
License: Apache-2.0
"""
from __future__ import annotations

import enum
from typing import Dict, List, Tuple

import numpy as np


class ExcitationFamily(enum.Enum):
    """Canonical excitation families for behavioral probing."""
    LOGIC = "logic"
    NARRATIVE = "narrative"
    MEMORY = "memory"
    ADVERSARIAL = "adversarial"
    METACOGNITIVE = "metacognitive"


class CoverageAnalyzer:
    """Variance-based coverage entropy and PCA coverage analysis.

    Operates on response embedding matrices (N_responses x D_dimensions).
    """

    @staticmethod
    def compute_coverage_entropy(matrix: np.ndarray) -> float:
        """Compute coverage entropy H_cov from variance proportions.

        H_cov(U) = -sum(p_d * log2(p_d))

        Args:
            matrix: Shape (N, D) — N response embeddings of dimension D.

        Returns:
            Shannon entropy of variance proportions in bits.

        Raises:
            ValueError: If matrix has fewer than 2 rows or is not 2D.
        """
        if matrix.ndim != 2:
            raise ValueError(f"Expected 2D matrix, got {matrix.ndim}D")
        if matrix.shape[0] < 2:
            raise ValueError(f"Need >= 2 rows for variance, got {matrix.shape[0]}")

        variances = np.var(matrix, axis=0, ddof=1)
        total_var = np.sum(variances)

        if total_var < 1e-15:
            return 0.0

        p_d = variances / total_var
        # Filter zero-variance dimensions to avoid log2(0)
        mask = p_d > 1e-15
        p_active = p_d[mask]

        entropy = -np.sum(p_active * np.log2(p_active))
        return float(entropy)

    @staticmethod
    def compute_pca_coverage(
        matrix: np.ndarray,
        n_components: int = 0,
    ) -> np.ndarray:
        """PCA via eigendecomposition of covariance matrix.

        Uses np.linalg.eigh on the symmetric covariance matrix.

        Args:
            matrix: Shape (N, D).
            n_components: Number of principal components to return.
                          0 = all components (min(N-1, D)).

        Returns:
            Variance ratios array of shape (n_components,), sorted descending.
        """
        if matrix.ndim != 2:
            raise ValueError(f"Expected 2D matrix, got {matrix.ndim}D")

        n, d = matrix.shape
        if n < 2:
            raise ValueError(f"Need >= 2 samples, got {n}")

        max_components = min(n - 1, d)
        if n_components <= 0:
            n_components = max_components
        n_components = min(n_components, max_components)

        centered = matrix - np.mean(matrix, axis=0)
        cov = np.dot(centered.T, centered) / (n - 1)

        eigenvalues, _ = np.linalg.eigh(cov)
        # eigh returns ascending order; reverse for descending
        eigenvalues = eigenvalues[::-1]
        # Clamp negative eigenvalues from numerical noise
        eigenvalues = np.maximum(eigenvalues, 0.0)

        total = np.sum(eigenvalues)
        if total < 1e-15:
            return np.zeros(n_components, dtype=np.float64)

        variance_ratios = eigenvalues[:n_components] / total
        return variance_ratios

    @staticmethod
    def identify_blind_spots(
        variance_ratios: np.ndarray,
        threshold: float = 0.01,
    ) -> List[int]:
        """Identify dimensions with negligible variance (blind spots).

        Args:
            variance_ratios: Sorted descending variance ratio per component.
            threshold: Components below this ratio are blind spots.

        Returns:
            List of component indices (0-based) below threshold.
        """
        indices: List[int] = []
        for i, ratio in enumerate(variance_ratios):
            if ratio < threshold:
                indices.append(i)
        return indices


class MutualInformationEstimator:
    """Histogram-based mutual information estimation (numpy-only)."""

    @staticmethod
    def estimate_mi(
        x: np.ndarray,
        y: np.ndarray,
        bins: int = 10,
    ) -> float:
        """Estimate mutual information I(X; Y) via 2D histogram.

        I(X; Y) = sum_{x,y} p(x,y) * log2(p(x,y) / (p(x) * p(y)))

        Args:
            x: 1D array of N samples.
            y: 1D array of N samples.
            bins: Number of histogram bins per axis.

        Returns:
            Mutual information in bits.
        """
        if x.shape[0] != y.shape[0]:
            raise ValueError(
                f"x and y must have same length: {x.shape[0]} != {y.shape[0]}"
            )

        # Joint histogram
        joint, _, _ = np.histogram2d(x.ravel(), y.ravel(), bins=bins)
        joint = joint / np.sum(joint)  # normalize to joint probability

        # Marginals
        p_x = np.sum(joint, axis=1)
        p_y = np.sum(joint, axis=0)

        # Outer product of marginals
        p_xy_independent = np.outer(p_x, p_y)

        # Mask zero cells
        nonzero = (joint > 1e-15) & (p_xy_independent > 1e-15)

        mi = np.sum(
            joint[nonzero] * np.log2(joint[nonzero] / p_xy_independent[nonzero])
        )
        return float(mi)

    @staticmethod
    def verify_orthogonality(
        families: Dict[str, np.ndarray],
        bins: int = 10,
    ) -> Dict[Tuple[str, str], float]:
        """Compute pairwise MI between all excitation families.

        Args:
            families: Map of family_name -> 1D score array.
            bins: Histogram bins for MI estimation.

        Returns:
            Dict mapping (family_a, family_b) -> MI value in bits.
        """
        estimator = MutualInformationEstimator()
        keys = sorted(families.keys())
        results: Dict[Tuple[str, str], float] = {}

        for i, k_a in enumerate(keys):
            for k_b in keys[i + 1:]:
                mi = estimator.estimate_mi(families[k_a], families[k_b], bins=bins)
                results[(k_a, k_b)] = mi

        return results
