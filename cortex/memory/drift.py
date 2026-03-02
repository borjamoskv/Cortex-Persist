"""CORTEX v8 — Drift Monitor (Topological Stability Engine).

Detects catastrophic drift in the L2 vector space before recall degrades
silently. Uses 3 computationally honest proxies instead of theoretical TDA:

1. Spectral Gap   — λ₁/λ₂ of covariance.  Detects cluster collapse.  O(n·d²).
2. Intrinsic Dim  — MLE (Levina-Bickel 2004) with JL projection.     O(n·k·d).
3. Page-Hinkley   — Streaming change-point detection.                 O(1)/update.

Zero new required dependencies — numpy only (already in project).
scipy.spatial.cKDTree is opt-in for intrinsic dimensionality (brute-force fallback).

Stratified anchoring: different stability thresholds per fact_type.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final

import numpy as np

__all__ = ["DriftMonitor", "DriftSignature"]

logger = logging.getLogger("cortex.memory.drift")


# ─── Stability Strata ────────────────────────────────────────────────

STRATA: Final[dict[str, dict[str, Any]]] = {
    "core": {"max_drift": 0.05, "types": frozenset({"axiom", "decision", "rule", "bridge"})},
    "active": {"max_drift": 0.15, "types": frozenset({"knowledge", "error", "config"})},
    "liminal": {"max_drift": 0.50, "types": frozenset({"ghost", "intent", "schema"})},
    "ephemeral": {"max_drift": float("inf"), "types": frozenset({"phantom", "test"})},
}


def stratum_for_type(fact_type: str) -> str:
    """Return the stability stratum name for a fact_type."""
    for name, cfg in STRATA.items():
        if fact_type in cfg["types"]:
            return name
    return "active"  # default


# ─── Drift Signature ─────────────────────────────────────────────────


@dataclass(frozen=True)
class DriftSignature:
    """Immutable topological snapshot of the vector space at time t.

    Versioned with model_hash so the signature auto-invalidates
    when the embedding model changes.
    """

    centroid: tuple[float, ...]
    spectral_gap: float
    intrinsic_dim: float | None  # None if scipy unavailable
    n_vectors: int
    model_hash: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["centroid"] = list(d["centroid"])
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DriftSignature:
        d = dict(d)  # shallow copy
        d["centroid"] = tuple(d["centroid"])
        return cls(**d)

    def save(self, path: Path) -> None:
        """Persist signature to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict()), encoding="utf-8")
        logger.debug("Drift signature saved to %s", path)

    @classmethod
    def load(cls, path: Path) -> DriftSignature | None:
        """Load signature from JSON. Returns None if missing/corrupt."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Failed to load drift signature: %s", exc)
            return None


# ─── Page-Hinkley Stream Detector ────────────────────────────────────


@dataclass
class PageHinkley:
    """O(1) streaming change-point detection (Page-Hinkley test).

    Detects shifts in the mean of a scalar stream without fixed windows.
    """

    threshold: float = 50.0
    delta: float = 0.01  # tolerated magnitude of change

    _cumsum: float = field(default=0.0, init=False, repr=False)
    _min_cumsum: float = field(default=float("inf"), init=False, repr=False)
    _count: int = field(default=0, init=False, repr=False)
    _mean: float = field(default=0.0, init=False, repr=False)

    def update(self, value: float) -> bool:
        """Feed one observation. Returns True if drift detected."""
        self._count += 1
        self._mean += (value - self._mean) / self._count
        self._cumsum += value - self._mean - self.delta
        self._min_cumsum = min(self._min_cumsum, self._cumsum)
        return (self._cumsum - self._min_cumsum) > self.threshold

    def reset(self) -> None:
        self._cumsum = 0.0
        self._min_cumsum = float("inf")
        self._count = 0
        self._mean = 0.0


# ─── Core Computations ───────────────────────────────────────────────


def spectral_gap(embeddings: np.ndarray) -> float:
    """Ratio λ₁/λ₂ of the covariance matrix. O(n·d²).

    High → one dominant direction (structured).
    Low  → isotropic (possible collapse or noise).
    """
    if embeddings.shape[0] < 3:
        return 1.0  # insufficient data

    cov = np.cov(embeddings, rowvar=False)
    # Top-2 eigenvalues only (eigvalsh returns ascending order)
    eigenvalues = np.linalg.eigvalsh(cov)[-2:]
    denom = max(float(eigenvalues[-2]), 1e-10)
    return float(eigenvalues[-1] / denom)


def intrinsic_dimensionality(
    embeddings: np.ndarray,
    k: int = 10,
    projection_dim: int = 64,
) -> float | None:
    """MLE intrinsic dimensionality (Levina-Bickel 2004).

    Applies JL projection to defeat the curse of dimensionality.
    Returns None if scipy is unavailable (opt-in dependency).

    O(n·k·d) after projection.
    """
    n, d = embeddings.shape
    if n < k + 1:
        return None

    # Johnson-Lindenstrauss projection to lower dim
    if d > projection_dim:
        rng = np.random.default_rng(42)
        proj = rng.standard_normal((d, projection_dim)) / np.sqrt(projection_dim)
        embeddings = embeddings @ proj

    # Try scipy for fast k-NN
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(embeddings)
        dists, _ = tree.query(embeddings, k=k + 1)
    except ImportError:
        # Brute-force fallback — O(n²) but zero deps
        from numpy.linalg import norm

        all_dists = np.array([norm(embeddings - embeddings[i], axis=1) for i in range(n)])
        # Sort and take k+1 nearest (including self)
        indices = np.argpartition(all_dists, k + 1, axis=1)[:, : k + 1]
        dists = np.take_along_axis(all_dists, indices, axis=1)
        dists.sort(axis=1)

    # Exclude self-distance (first column)
    dists = dists[:, 1:]

    # MLE: d̂ = 1 / mean(log(r_k / r_j))
    log_dists = np.log(np.maximum(dists, 1e-10))
    log_rk = log_dists[:, -1:]  # max distance per point
    diff = log_rk - log_dists[:, :-1]  # (n, k-1)

    # Average over k-1 neighbors per point
    with np.errstate(divide="ignore", invalid="ignore"):
        estimates = (k - 1) / np.sum(diff, axis=1)

    # Filter inf/nan, take median for robustness
    valid = estimates[np.isfinite(estimates)]
    if len(valid) == 0:
        return None

    return float(np.median(valid))


def centroid_drift(
    current_centroid: np.ndarray,
    baseline_centroid: np.ndarray,
) -> float:
    """Normalized L2 distance between centroids.

    Normalized by the baseline centroid norm to make drift comparable
    across embedding spaces of different scales.
    """
    baseline_norm = max(float(np.linalg.norm(baseline_centroid)), 1e-10)
    return float(np.linalg.norm(current_centroid - baseline_centroid) / baseline_norm)


# ─── Drift Monitor ───────────────────────────────────────────────────


class DriftMonitor:
    """Monitors topological health of the L2 vector space.

    Usage:
        monitor = DriftMonitor(model_hash="miniLM-L6-v2")
        sig = monitor.checkpoint(embeddings)    # baseline
        ...
        health = monitor.health(embeddings, sig)
    """

    __slots__ = ("_model_hash", "_page_hinkley", "_signature_path")

    def __init__(
        self,
        model_hash: str,
        signature_dir: Path | None = None,
    ) -> None:
        self._model_hash = model_hash
        self._page_hinkley = PageHinkley()
        self._signature_path = (signature_dir / "drift_baseline.json") if signature_dir else None

    @property
    def model_hash(self) -> str:
        return self._model_hash

    def checkpoint(self, embeddings: np.ndarray) -> DriftSignature:
        """Compute and optionally persist a drift signature (baseline).

        Call this after bulk loads or during maintenance windows.
        """
        centroid = tuple(float(x) for x in embeddings.mean(axis=0))
        sg = spectral_gap(embeddings)
        idim = intrinsic_dimensionality(embeddings)

        sig = DriftSignature(
            centroid=centroid,
            spectral_gap=sg,
            intrinsic_dim=idim,
            n_vectors=embeddings.shape[0],
            model_hash=self._model_hash,
        )

        if self._signature_path:
            sig.save(self._signature_path)

        # Reset Page-Hinkley on new baseline
        self._page_hinkley.reset()

        logger.info(
            "Drift checkpoint: n=%d, spectral_gap=%.3f, intrinsic_dim=%s",
            sig.n_vectors,
            sig.spectral_gap,
            f"{sig.intrinsic_dim:.1f}" if sig.intrinsic_dim is not None else "N/A",
        )
        return sig

    def health(
        self,
        embeddings: np.ndarray,
        baseline: DriftSignature | None = None,
    ) -> dict[str, Any]:
        """Compute health metrics against a baseline.

        Returns dict with:
            - topological_health: float 0.0–1.0
            - centroid_drift: float
            - spectral_ratio: float (current / baseline)
            - intrinsic_dim_ratio: float | None
            - page_hinkley_alert: bool
            - model_valid: bool
            - detail: str
        """
        # Load baseline from disk if not provided
        if baseline is None and self._signature_path:
            baseline = DriftSignature.load(self._signature_path)

        if baseline is None:
            return {
                "topological_health": 1.0,
                "centroid_drift": 0.0,
                "spectral_ratio": 1.0,
                "intrinsic_dim_ratio": None,
                "page_hinkley_alert": False,
                "model_valid": True,
                "detail": "No baseline — first checkpoint needed",
            }

        # Model hash validation
        model_valid = baseline.model_hash == self._model_hash
        if not model_valid:
            return {
                "topological_health": 0.0,
                "centroid_drift": float("inf"),
                "spectral_ratio": 0.0,
                "intrinsic_dim_ratio": None,
                "page_hinkley_alert": True,
                "model_valid": False,
                "detail": (
                    f"Model changed: baseline={baseline.model_hash}, "
                    f"current={self._model_hash}. Recalculate baseline."
                ),
            }

        # Compute current metrics
        current_centroid = embeddings.mean(axis=0)
        baseline_centroid = np.array(baseline.centroid)

        drift = centroid_drift(current_centroid, baseline_centroid)
        current_sg = spectral_gap(embeddings)
        sg_ratio = current_sg / max(baseline.spectral_gap, 1e-10)

        # Intrinsic dimensionality (optional)
        current_idim = intrinsic_dimensionality(embeddings)
        idim_ratio = None
        if current_idim is not None and baseline.intrinsic_dim is not None:
            idim_ratio = current_idim / max(baseline.intrinsic_dim, 1e-10)

        # Page-Hinkley update with centroid drift
        ph_alert = self._page_hinkley.update(drift)

        # Composite health score: weighted average of proxy signals
        # Each proxy contributes to [0, 1] where 1 = healthy
        health_components: list[float] = []

        # Centroid drift: healthy if < 0.15 (active stratum default)
        drift_score = max(0.0, 1.0 - drift / 0.15)
        health_components.append(drift_score)

        # Spectral ratio: healthy if close to 1.0 (between 0.5 and 2.0)
        sg_score = max(0.0, 1.0 - abs(sg_ratio - 1.0))
        health_components.append(sg_score)

        # Intrinsic dim ratio: healthy if close to 1.0
        if idim_ratio is not None:
            idim_score = max(0.0, 1.0 - abs(idim_ratio - 1.0) * 0.5)
            health_components.append(idim_score)

        topological_health = sum(health_components) / len(health_components)

        # Page-Hinkley override: if streaming detector fires, cap health
        if ph_alert:
            topological_health = min(topological_health, 0.4)

        # Build detail message
        details: list[str] = [
            f"drift={drift:.4f}",
            f"spectral_ratio={sg_ratio:.3f}",
        ]
        if idim_ratio is not None:
            details.append(f"idim_ratio={idim_ratio:.3f}")
        if ph_alert:
            details.append("PAGE_HINKLEY_ALERT")

        return {
            "topological_health": round(topological_health, 4),
            "centroid_drift": round(drift, 6),
            "spectral_ratio": round(sg_ratio, 4),
            "intrinsic_dim_ratio": round(idim_ratio, 4) if idim_ratio is not None else None,
            "page_hinkley_alert": ph_alert,
            "model_valid": model_valid,
            "detail": " | ".join(details),
        }

    def load_baseline(self) -> DriftSignature | None:
        """Load persisted baseline signature."""
        if self._signature_path:
            return DriftSignature.load(self._signature_path)
        return None


def model_hash_from_name(model_name: str) -> str:
    """Derive a stable hash from a model identifier string."""
    return hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:16]
