import math
from enum import Enum

import numpy as np


class ExcitationFamily(Enum):
    LOGIC = "L"
    NARRATIVE = "N"
    MEMORY = "M"
    ADVERSARIAL = "A"
    METACOGNITIVE = "Mc"


class CoverageAnalyzer:
    def __init__(self):
        pass

    def compute_coverage_entropy(self, matrix: np.ndarray) -> float:
        """
        Computes Coverage Entropy (H_cov) over the behavioral metrics matrix.
        H_cov(U) = -sum(p_d * log2(p_d))
        where p_d is the proportion of total variance explained by dimension d.
        """
        if matrix.size == 0 or matrix.shape[0] < 2:
            return 0.0

        # Center the matrix
        centered = matrix - np.mean(matrix, axis=0)

        # Compute variances of each dimension
        variances = np.var(centered, axis=0)
        total_var = np.sum(variances)
        if total_var == 0:
            return 0.0

        probs = variances / total_var
        probs = probs[probs > 0]

        return float(-np.sum(probs * np.log2(probs)))

    def compute_pca_coverage(self, matrix: np.ndarray, n_components: int) -> np.ndarray:
        """
        Computes PCA explained variance ratios using eigendecomposition (np.linalg.eigh).
        """
        if matrix.size == 0 or matrix.shape[0] < 2:
            return np.zeros(n_components)

        # Center the data
        centered = matrix - np.mean(matrix, axis=0)

        # Compute covariance matrix
        cov = np.cov(centered, rowvar=False)
        if cov.ndim == 0:
            return np.array([1.0])

        # Eigendecomposition (eigh is optimized for symmetric matrices)
        eigenvalues, _ = np.linalg.eigh(cov)

        # Sort in descending order
        eigenvalues = np.sort(eigenvalues)[::-1]

        total_eigval = np.sum(eigenvalues)
        if total_eigval == 0:
            return np.zeros(n_components)

        explained_variance_ratio = eigenvalues / total_eigval

        # Pad or truncate to match n_components
        if len(explained_variance_ratio) < n_components:
            padding = np.zeros(n_components - len(explained_variance_ratio))
            explained_variance_ratio = np.concatenate([explained_variance_ratio, padding])
        else:
            explained_variance_ratio = explained_variance_ratio[:n_components]

        return explained_variance_ratio

    def identify_blind_spots(
        self, variance_ratios: np.ndarray, threshold: float = 0.05
    ) -> list[int]:
        """
        Identifies dimensions with variance contribution lower than threshold.
        """
        return [int(i) for i, r in enumerate(variance_ratios) if r < threshold]

    def recommend_excitations(
        self, blind_spots: list[int], dimension_family_mapping: dict[int, ExcitationFamily]
    ) -> dict[ExcitationFamily, float]:
        """
        Recommends weight changes for families that correspond to under-excited dimensions.
        """
        recommendations = {}
        for spot in blind_spots:
            family = dimension_family_mapping.get(spot)
            if family:
                recommendations[family] = recommendations.get(family, 0.0) + 0.25
        return recommendations


class MutualInformationEstimator:
    def __init__(self):
        pass

    def estimate_mi(self, x: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
        """
        Estimates Mutual Information I(X;Y) between two continuous variable series
        using 2D histogram frequency approximation.
        I(X;Y) = sum_{x,y} p(x,y) log2( p(x,y) / (p(x)p(y)) )
        """
        if x.size == 0 or y.size == 0 or len(x) != len(y):
            return 0.0

        # Calculate joint and marginal histograms
        c_xy, _, _ = np.histogram2d(x, y, bins=bins)
        c_x, _ = np.histogram(x, bins=bins)
        c_y, _ = np.histogram(y, bins=bins)

        # Normalize to probabilities
        n_samples = np.sum(c_xy)
        if n_samples == 0:
            return 0.0

        p_xy = c_xy / n_samples
        p_x = c_x / n_samples
        p_y = c_y / n_samples

        mi = 0.0
        for i in range(bins):
            for j in range(bins):
                if p_xy[i, j] > 0 and p_x[i] > 0 and p_y[j] > 0:
                    mi += p_xy[i, j] * math.log2(p_xy[i, j] / (p_x[i] * p_y[j]))

        return float(mi)

    def verify_orthogonality(
        self, family_vectors: dict[ExcitationFamily, np.ndarray], threshold: float = 0.1
    ) -> dict[tuple[ExcitationFamily, ExcitationFamily], float]:
        """
        Computes pairwise Mutual Information to verify orthogonality (low mutual info).
        """
        results = {}
        families = list(family_vectors.keys())
        for i in range(len(families)):
            for j in range(i + 1, len(families)):
                fam_a = families[i]
                fam_b = families[j]

                vec_a = family_vectors[fam_a]
                vec_b = family_vectors[fam_b]

                # Check for matching dimensions
                min_len = min(len(vec_a), len(vec_b))
                if min_len > 1:
                    mi = self.estimate_mi(vec_a[:min_len], vec_b[:min_len])
                    results[(fam_a, fam_b)] = mi
        return results
