"""Tests for cortex.memory.drift — Topological Stability Engine.

Tests the 3 computational proxies (spectral gap, intrinsic dimensionality,
Page-Hinkley), DriftSignature serialization, DriftMonitor health computation,
stratified anchoring, and model_hash invalidation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from cortex.memory.drift import (
    STRATA,
    DriftMonitor,
    DriftSignature,
    PageHinkley,
    centroid_drift,
    intrinsic_dimensionality,
    model_hash_from_name,
    spectral_gap,
    stratum_for_type,
)

# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def rng():
    """Deterministic RNG for reproducible tests."""
    return np.random.default_rng(42)


@pytest.fixture
def stable_embeddings(rng):
    """100 vectors in 384D from a well-structured distribution (3 clusters)."""
    cluster_a = rng.normal(loc=1.0, scale=0.2, size=(34, 384))
    cluster_b = rng.normal(loc=-1.0, scale=0.2, size=(33, 384))
    cluster_c = rng.normal(loc=0.0, scale=0.2, size=(33, 384))
    return np.vstack([cluster_a, cluster_b, cluster_c]).astype(np.float32)


@pytest.fixture
def drifted_embeddings(rng):
    """Embeddings that have drifted significantly from stable_embeddings."""
    # All in one cluster — topology collapsed
    return rng.normal(loc=5.0, scale=0.1, size=(100, 384)).astype(np.float32)


@pytest.fixture
def tiny_embeddings(rng):
    """Too few vectors for meaningful analysis."""
    return rng.normal(size=(2, 384)).astype(np.float32)


@pytest.fixture
def sig_dir():
    """Temporary directory for drift signatures."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


# ─── Spectral Gap ─────────────────────────────────────────────────────


class TestSpectralGap:
    def test_returns_positive_float(self, stable_embeddings):
        sg = spectral_gap(stable_embeddings)
        assert isinstance(sg, float)
        assert sg > 0

    def test_clustered_has_high_gap(self, stable_embeddings):
        """Well-separated clusters → high spectral gap (dominant direction)."""
        sg = spectral_gap(stable_embeddings)
        assert sg > 1.0

    def test_isotropic_has_low_gap(self, rng):
        """Isotropic noise → spectral gap close to 1.0."""
        isotropic = rng.normal(size=(200, 384)).astype(np.float32)
        sg = spectral_gap(isotropic)
        assert 0.5 < sg < 3.0  # should be near 1.0 for isotropic

    def test_insufficient_data_fallback(self, rng):
        """< 3 vectors → returns 1.0 (insufficient data signal)."""
        tiny = rng.normal(size=(2, 384))
        assert spectral_gap(tiny) == 1.0

    def test_deterministic(self, stable_embeddings):
        """Same input → same output."""
        assert spectral_gap(stable_embeddings) == spectral_gap(stable_embeddings)


# ─── Intrinsic Dimensionality ────────────────────────────────────────


class TestIntrinsicDimensionality:
    def test_returns_float_or_none(self, stable_embeddings):
        result = intrinsic_dimensionality(stable_embeddings)
        assert result is None or isinstance(result, float)

    def test_low_dim_manifold(self, rng):
        """Data on a ~5D manifold should estimate low intrinsic dim."""
        # Generate 5D data and embed in 384D
        low_dim = rng.normal(size=(200, 5))
        projection = rng.normal(size=(5, 384))
        embedded = (low_dim @ projection).astype(np.float32)

        result = intrinsic_dimensionality(embedded, k=10)
        if result is not None:
            # Should estimate close to 5 (±generous margin)
            assert 2 < result < 20

    def test_insufficient_data(self, rng):
        """< k+1 vectors → returns None."""
        tiny = rng.normal(size=(5, 384))
        result = intrinsic_dimensionality(tiny, k=10)
        assert result is None

    def test_jl_projection_applied(self, rng):
        """High-D input gets projected — should not error."""
        high_d = rng.normal(size=(100, 1024))
        result = intrinsic_dimensionality(high_d)
        # Should work without error regardless of scipy availability
        assert result is None or isinstance(result, float)


# ─── Page-Hinkley ────────────────────────────────────────────────────


class TestPageHinkley:
    def test_no_drift_stable_signal(self):
        """Constant signal → no drift detected."""
        ph = PageHinkley(threshold=50.0)
        alerts = [ph.update(1.0) for _ in range(100)]
        assert not any(alerts)

    def test_detects_mean_shift(self):
        """Sudden mean shift → drift detected."""
        ph = PageHinkley(threshold=10.0)

        # Stable phase
        for _ in range(50):
            ph.update(0.0)

        # Shifted phase
        detected = False
        for _ in range(50):
            if ph.update(5.0):
                detected = True
                break

        assert detected, "Page-Hinkley should detect mean shift"

    def test_reset_clears_state(self):
        """Reset makes the detector forget previous observations."""
        ph = PageHinkley(threshold=10.0)
        for _ in range(50):
            ph.update(5.0)

        ph.reset()
        # After reset, stable signal should not trigger
        alerts = [ph.update(0.0) for _ in range(30)]
        assert not any(alerts)


# ─── Centroid Drift ──────────────────────────────────────────────────


class TestCentroidDrift:
    def test_zero_drift_for_identical(self):
        a = np.array([1.0, 2.0, 3.0])
        assert centroid_drift(a, a) == 0.0

    def test_positive_for_different(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 0.0, 0.0])
        drift = centroid_drift(a, b)
        assert drift > 0

    def test_normalized_by_baseline_norm(self):
        """Drift should be normalized — moving 1 unit from a 10-norm baseline
        should be smaller than moving 1 unit from a 1-norm baseline."""
        shift = np.array([1.0, 0.0, 0.0])
        small_base = np.array([1.0, 0.0, 0.0])
        large_base = np.array([10.0, 0.0, 0.0])

        drift_small = centroid_drift(small_base + shift, small_base)
        drift_large = centroid_drift(large_base + shift, large_base)
        assert drift_large < drift_small


# ─── DriftSignature ──────────────────────────────────────────────────


class TestDriftSignature:
    def test_roundtrip_dict(self):
        sig = DriftSignature(
            centroid=(1.0, 2.0, 3.0),
            spectral_gap=5.5,
            intrinsic_dim=12.3,
            n_vectors=100,
            model_hash="abc123",
            timestamp=12345.0,
        )
        d = sig.to_dict()
        restored = DriftSignature.from_dict(d)
        assert restored == sig

    def test_roundtrip_json_file(self, sig_dir):
        sig = DriftSignature(
            centroid=(0.5, -0.5),
            spectral_gap=3.14,
            intrinsic_dim=None,
            n_vectors=50,
            model_hash="test_model",
        )
        path = sig_dir / "test_sig.json"
        sig.save(path)

        loaded = DriftSignature.load(path)
        assert loaded is not None
        assert loaded.centroid == sig.centroid
        assert loaded.spectral_gap == sig.spectral_gap
        assert loaded.model_hash == sig.model_hash

    def test_load_missing_returns_none(self, sig_dir):
        assert DriftSignature.load(sig_dir / "nonexistent.json") is None

    def test_load_corrupt_returns_none(self, sig_dir):
        path = sig_dir / "corrupt.json"
        path.write_text("not valid json{{{", encoding="utf-8")
        assert DriftSignature.load(path) is None

    def test_frozen(self):
        sig = DriftSignature(
            centroid=(1.0,),
            spectral_gap=1.0,
            intrinsic_dim=None,
            n_vectors=1,
            model_hash="x",
        )
        with pytest.raises(AttributeError):
            sig.spectral_gap = 2.0  # type: ignore[misc]


# ─── Drift Monitor ──────────────────────────────────────────────────


class TestDriftMonitor:
    def test_checkpoint_creates_signature(self, stable_embeddings, sig_dir):
        monitor = DriftMonitor(model_hash="test_hash", signature_dir=sig_dir)
        sig = monitor.checkpoint(stable_embeddings)

        assert sig.n_vectors == 100
        assert sig.model_hash == "test_hash"
        assert sig.spectral_gap > 0
        assert len(sig.centroid) == 384

    def test_checkpoint_persists(self, stable_embeddings, sig_dir):
        monitor = DriftMonitor(model_hash="test_hash", signature_dir=sig_dir)
        monitor.checkpoint(stable_embeddings)

        # Should persist to disk
        sig_path = sig_dir / "drift_baseline.json"
        assert sig_path.exists()
        data = json.loads(sig_path.read_text())
        assert data["model_hash"] == "test_hash"

    def test_health_no_baseline(self, stable_embeddings):
        monitor = DriftMonitor(model_hash="test")
        result = monitor.health(stable_embeddings)
        assert result["topological_health"] == 1.0
        assert result["detail"] == "No baseline — first checkpoint needed"

    def test_health_healthy_vectors(self, stable_embeddings, sig_dir):
        monitor = DriftMonitor(model_hash="test", signature_dir=sig_dir)
        baseline = monitor.checkpoint(stable_embeddings)

        # Same embeddings → healthy
        result = monitor.health(stable_embeddings, baseline)
        assert result["topological_health"] > 0.8
        assert result["model_valid"] is True
        assert result["centroid_drift"] < 0.01

    def test_health_drifted_vectors(self, stable_embeddings, drifted_embeddings, sig_dir):
        monitor = DriftMonitor(model_hash="test", signature_dir=sig_dir)
        baseline = monitor.checkpoint(stable_embeddings)

        # Drifted embeddings → low health
        result = monitor.health(drifted_embeddings, baseline)
        assert result["topological_health"] < 0.5
        assert result["centroid_drift"] > 0.1

    def test_model_hash_invalidation(self, stable_embeddings, sig_dir):
        """Changed model hash → health = 0, model_valid = False."""
        monitor_v1 = DriftMonitor(model_hash="model_v1", signature_dir=sig_dir)
        baseline = monitor_v1.checkpoint(stable_embeddings)

        monitor_v2 = DriftMonitor(model_hash="model_v2", signature_dir=sig_dir)
        result = monitor_v2.health(stable_embeddings, baseline)

        assert result["topological_health"] == 0.0
        assert result["model_valid"] is False
        assert "Recalculate baseline" in result["detail"]

    def test_load_baseline(self, stable_embeddings, sig_dir):
        monitor = DriftMonitor(model_hash="test", signature_dir=sig_dir)
        monitor.checkpoint(stable_embeddings)

        loaded = monitor.load_baseline()
        assert loaded is not None
        assert loaded.model_hash == "test"
        assert loaded.n_vectors == 100


# ─── Strata ──────────────────────────────────────────────────────────


class TestStrata:
    def test_core_types(self):
        for t in ("axiom", "decision", "rule", "bridge"):
            assert stratum_for_type(t) == "core"

    def test_active_types(self):
        for t in ("knowledge", "error", "config"):
            assert stratum_for_type(t) == "active"

    def test_liminal_types(self):
        for t in ("ghost", "intent", "schema"):
            assert stratum_for_type(t) == "liminal"

    def test_unknown_defaults_active(self):
        assert stratum_for_type("foobar") == "active"

    def test_strata_max_drift_ordering(self):
        """Core should be strictest, ephemeral most permissive."""
        assert STRATA["core"]["max_drift"] < STRATA["active"]["max_drift"]
        assert STRATA["active"]["max_drift"] < STRATA["liminal"]["max_drift"]
        assert STRATA["liminal"]["max_drift"] < STRATA["ephemeral"]["max_drift"]


# ─── model_hash_from_name ───────────────────────────────────────────


class TestModelHash:
    def test_deterministic(self):
        a = model_hash_from_name("all-MiniLM-L6-v2")
        b = model_hash_from_name("all-MiniLM-L6-v2")
        assert a == b

    def test_different_models_different_hashes(self):
        a = model_hash_from_name("all-MiniLM-L6-v2")
        b = model_hash_from_name("text-embedding-ada-002")
        assert a != b

    def test_returns_16_char_hex(self):
        h = model_hash_from_name("test")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


# ─── DriftAlert Model ────────────────────────────────────────────────


class TestDriftAlert:
    def test_alert_creation(self):
        from cortex.daemon.models import DriftAlert

        alert = DriftAlert(
            health=0.35,
            centroid_drift=0.23,
            spectral_ratio=0.6,
            n_vectors=500,
            message="Vector space drift detected",
        )
        assert alert.health == 0.35
        assert alert.n_vectors == 500

    def test_alert_in_daemon_status(self):
        from cortex.daemon.models import DaemonStatus, DriftAlert

        status = DaemonStatus(
            checked_at="2026-03-02T17:00:00",
            drift_alerts=[
                DriftAlert(
                    health=0.3,
                    centroid_drift=0.5,
                    spectral_ratio=0.4,
                    n_vectors=100,
                    message="test",
                )
            ],
        )
        assert not status.all_healthy
        d = status.to_dict()
        assert len(d["drift_alerts"]) == 1
        assert d["drift_alerts"][0]["health"] == 0.3
