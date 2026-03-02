"""
CORTEX v7 — Topological Health Monitor (130/100 Sovereign Standard).

Breaks the circular Bayesian confirmation loop: reference signatures (p_0)
are versioned against the exact embedding model that generated them.

If the model mutates (fine-tuning, version bump, swap), the anchor
becomes invalid and MUST be recalculated in cold mode before the
SemanticMutator is allowed to continue writing.

The trap: measuring drift with the same embeddings being drifted
creates a self-confirming loop. This module enforces epistemic hygiene.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from cortex.memory.encoder import AsyncEncoder

__all__ = [
    "TopologicalAnchor",
    "TopologicalHealthMonitor",
    "AnchorInvalidError",
    "ProxyType",
]

logger = logging.getLogger("cortex.memory.topological_health")

ProxyType = Literal["spectral_gap", "intrinsic_dim", "hubness"]


class AnchorInvalidError(RuntimeError):
    """Raised when attempting to measure drift with an invalidated anchor.

    The model_hash of the current embedder does not match the anchor's
    model_hash. Recalculate p_0 in cold mode before continuing.
    """


@dataclass(frozen=True)
class TopologicalAnchor:
    """Frozen reference signature for topological health measurement.

    The triple (signature, timestamp, model_hash) is the epistemic atom:
    - signature: distributional fingerprint of the latent space at t_0
    - timestamp: when the measurement was taken
    - model_hash: SHA-256 of the embedder that produced the signature

    If model_hash drifts, the anchor is SILENTLY INVALID. This class
    makes that invalidation LOUD and BLOCKING.
    """

    mean_vector: bytes  # np.float32 serialized mean of sampled vectors
    variance_trace: float  # tr(Cov) — scalar summary of spread
    spectral_gap: float  # λ₁ - λ₂
    intrinsic_dim: float  # (∑λ_i)² / ∑λ_i², participation ratio
    hubness: float  # variance of in-degree in local KNN graph
    timestamp: float  # t_0: epoch seconds
    model_hash: str  # SHA-256 of the embedder identity
    sample_size: int  # N vectors used to compute this anchor


class TopologicalHealthMonitor:
    """Guard against circular Bayesian confirmation in topological drift.

    Usage:
        monitor = TopologicalHealthMonitor(encoder)
        anchor = monitor.compute_anchor(vectors)

        # ... time passes, mutations happen ...

        if monitor.needs_recalibration(anchor):
            anchor = monitor.compute_anchor(vectors)  # cold recalculation

        drift = monitor.measure_drift(vectors, anchor)  # safe measurement
    """

    __slots__ = (
        "_model_hash",
        "_rotation_interval",
        "_checkpoints_seen",
        "_active_proxy_idx",
        "_proxy_sequence",
        "_history_spectral",
        "_history_idim",
        "_history_hubness",
    )

    def __init__(self, encoder: AsyncEncoder, rotation_interval: int = 100) -> None:
        self._model_hash = encoder.model_identity_hash
        self._rotation_interval = rotation_interval
        self._checkpoints_seen = 0
        self._proxy_sequence: tuple[ProxyType, ...] = ("spectral_gap", "intrinsic_dim", "hubness")
        self._active_proxy_idx = 0

        # Keep recent history for correlation checking
        window_size = max(100, rotation_interval * 6)
        self._history_spectral: deque[float] = deque(maxlen=window_size)
        self._history_idim: deque[float] = deque(maxlen=window_size)
        self._history_hubness: deque[float] = deque(maxlen=window_size)

    def compute_anchor(
        self,
        vectors: list[list[float]] | np.ndarray,
    ) -> TopologicalAnchor:
        """Compute a frozen topological anchor from a sample of vectors.

        This MUST be called with vectors encoded by the CURRENT model.
        The resulting anchor is stamped with the current model_hash.
        """
        if isinstance(vectors, list):
            arr = np.array(vectors, dtype=np.float32)
        else:
            arr = vectors.astype(np.float32)

        if arr.ndim != 2 or arr.shape[0] < 2:
            raise ValueError(f"Need ≥2 vectors for anchor computation, got shape {arr.shape}")

        mean_vec = np.mean(arr, axis=0)
        # Trace of covariance = sum of variances along each dimension
        # Efficient O(N*D) without materializing full DxD covariance matrix
        variance_trace = float(np.sum(np.var(arr, axis=0)))

        spectral_gap, intrinsic_dim, hubness = self._compute_metrics(arr)

        return TopologicalAnchor(
            mean_vector=mean_vec.tobytes(),
            variance_trace=variance_trace,
            spectral_gap=spectral_gap,
            intrinsic_dim=intrinsic_dim,
            hubness=hubness,
            timestamp=time.time(),
            model_hash=self._model_hash,
            sample_size=arr.shape[0],
        )

    def validate_anchor(self, anchor: TopologicalAnchor) -> bool:
        """Check if the anchor is still valid for the current model.

        Returns False if model_hash has drifted — the anchor is
        epistemically useless and MUST be recalculated cold.
        """
        return anchor.model_hash == self._model_hash

    def needs_recalibration(self, anchor: TopologicalAnchor) -> bool:
        """Semantic inverse of validate_anchor for clarity at call sites."""
        return anchor.model_hash != self._model_hash

    def measure_drift(
        self,
        current_vectors: list[list[float]] | np.ndarray,
        anchor: TopologicalAnchor,
    ) -> float:
        """Measure topological drift from the anchor.

        Returns the L2 distance between current mean vector and anchor mean,
        plus the relative change in variance trace.

        Raises AnchorInvalidError if model_hash has drifted — you CANNOT
        measure drift with an invalidated anchor. That's the whole point.
        """
        if not self.validate_anchor(anchor):
            raise AnchorInvalidError(
                f"Model hash mismatch: anchor={anchor.model_hash[:12]}... "
                f"current={self._model_hash[:12]}... "
                f"Recalculate p_0 in cold mode before measuring drift."
            )

        if isinstance(current_vectors, list):
            arr = np.array(current_vectors, dtype=np.float32)
        else:
            arr = current_vectors.astype(np.float32)

        if arr.ndim != 2 or arr.shape[0] < 2:
            raise ValueError(f"Need ≥2 vectors for drift measurement, got shape {arr.shape}")

        # Reconstruct anchor's mean vector
        dim = arr.shape[1]
        anchor_mean = np.frombuffer(anchor.mean_vector, dtype=np.float32)
        if anchor_mean.shape[0] != dim:
            raise ValueError(f"Dimension mismatch: anchor={anchor_mean.shape[0]}, current={dim}")

        current_mean = np.mean(arr, axis=0)
        current_var_trace = float(np.sum(np.var(arr, axis=0)))
        current_spectral, current_idim, current_hubness = self._compute_metrics(arr)

        # L2 displacement of the centroid
        centroid_drift = float(np.linalg.norm(current_mean - anchor_mean))

        # Relative variance change (absolute to handle near-zero)
        if anchor.variance_trace > 1e-12:
            variance_drift = abs(current_var_trace - anchor.variance_trace) / anchor.variance_trace
        else:
            variance_drift = current_var_trace

        # Store in histories
        self._history_spectral.append(current_spectral)
        self._history_idim.append(current_idim)
        self._history_hubness.append(current_hubness)
        self._checkpoints_seen += 1

        # Check correlation periodically
        self._check_correlation_divergence()

        # Update active proxy
        if self._checkpoints_seen % self._rotation_interval == 0:
            self._active_proxy_idx = (self._active_proxy_idx + 1) % len(self._proxy_sequence)
            logger.info("TopologicalHealthMonitor: Rotating active proxy to %s", self.active_proxy)

        # Calculate structure drift based on the active proxy
        proxy = self.active_proxy
        if proxy == "spectral_gap":
            anchor_val, cur_val = anchor.spectral_gap, current_spectral
        elif proxy == "intrinsic_dim":
            anchor_val, cur_val = anchor.intrinsic_dim, current_idim
        else:
            anchor_val, cur_val = anchor.hubness, current_hubness

        if anchor_val > 1e-12:
            structure_drift = abs(cur_val - anchor_val) / anchor_val
        else:
            structure_drift = cur_val

        # Combined metric: centroid shift + variance instability + structure drift
        return centroid_drift + variance_drift + structure_drift

    @property
    def active_proxy(self) -> ProxyType:
        return self._proxy_sequence[self._active_proxy_idx]

    @staticmethod
    def _compute_metrics(arr: np.ndarray) -> tuple[float, float, float]:
        """Compute the three structural proxies to prevent Goodhart's Law."""
        cov_matrix = np.cov(arr, rowvar=False)
        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        eigenvalues = np.sort(eigenvalues)[::-1]  # descending

        # 1. Spectral Gap
        if len(eigenvalues) >= 2:
            spectral_gap = float(abs(eigenvalues[0] - eigenvalues[1]))
        else:
            spectral_gap = 0.0

        # 2. Intrinsic Dimension (Participation Ratio)
        sum_eig = np.sum(eigenvalues)
        sum_sq_eig = np.sum(eigenvalues**2)
        intrinsic_dim = float((sum_eig**2) / sum_sq_eig) if sum_sq_eig > 1e-12 else 1.0

        # 3. Hubness (using variance of in-degree in local KNN graph)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_arr = arr / norms
        similarity_matrix = np.dot(normalized_arr, normalized_arr.T)

        np.fill_diagonal(similarity_matrix, -1.0)

        k = min(10, arr.shape[0] - 1)
        if k > 0:
            knn_indices = np.argsort(similarity_matrix, axis=1)[:, -k:]
            in_degrees = np.zeros(arr.shape[0])
            for i in range(arr.shape[0]):
                for j in knn_indices[i]:
                    in_degrees[j] += 1
            hubness = float(np.var(in_degrees))
        else:
            hubness = 0.0

        return spectral_gap, intrinsic_dim, hubness

    def _check_correlation_divergence(self) -> None:
        """Detect if proxies diverge, indicating Goodhart's Law calcification."""
        if len(self._history_spectral) < 10:
            return  # Need sufficient samples

        arr_s = np.array(self._history_spectral)
        arr_i = np.array(self._history_idim)
        arr_h = np.array(self._history_hubness)

        # Pearson correlation
        if np.std(arr_s) > 1e-12 and np.std(arr_i) > 1e-12:
            corr_si = np.corrcoef(arr_s, arr_i)[0, 1]
        else:
            corr_si = 1.0

        if np.std(arr_i) > 1e-12 and np.std(arr_h) > 1e-12:
            corr_ih = np.corrcoef(arr_i, arr_h)[0, 1]
        else:
            corr_ih = 1.0

        # If absolute correlation drops below 0.3 for a prolonged period, warn.
        # (Using absolute because they might be inversely correlated but still informative)
        if abs(corr_si) < 0.3 and abs(corr_ih) < 0.3:
            logger.critical(
                "TopologicalHealthMonitor: PROXY DIVERGENCE DETECTED. "
                "Spectral gap, Intrinsic Dim, and Hubness have lost correlation "
                "(corr_si=%.2f, corr_ih=%.2f). "
                "Goodhart's Law may be calcifying the topology. Real signal lost.",
                corr_si,
                corr_ih,
            )
