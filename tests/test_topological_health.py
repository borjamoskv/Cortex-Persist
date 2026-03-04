"""Tests for Topological Health Monitor — circular Bayesian confirmation guard."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from cortex.memory.topological_health import (
    AnchorInvalidError,
    TopologicalAnchor,
    TopologicalHealthMonitor,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_encoder(model_hash: str = "abc123") -> MagicMock:
    """Create a mock encoder with a deterministic model_identity_hash."""
    encoder = MagicMock()
    encoder.model_identity_hash = model_hash
    return encoder


def _random_vectors(n: int = 50, dim: int = 384, seed: int = 42) -> np.ndarray:
    """Generate reproducible random vectors."""
    rng = np.random.default_rng(seed)
    vecs = rng.standard_normal((n, dim)).astype(np.float32)
    # L2 normalize like real embeddings
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


# ---------------------------------------------------------------------------
# Anchor Creation
# ---------------------------------------------------------------------------


class TestAnchorCreation:
    def test_anchor_captures_model_hash(self):
        """Anchor must be stamped with the model_hash at creation time."""
        encoder = _make_mock_encoder("model_v1_hash")
        monitor = TopologicalHealthMonitor(encoder)
        vectors = _random_vectors(10, 8)

        anchor = monitor.compute_anchor(vectors)

        assert anchor.model_hash == "model_v1_hash"
        assert anchor.sample_size == 10
        assert anchor.timestamp <= time.time()

    def test_anchor_is_frozen(self):
        """TopologicalAnchor is immutable — cannot be silently mutated."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)
        anchor = monitor.compute_anchor(_random_vectors(5, 8))

        with pytest.raises(AttributeError):
            anchor.model_hash = "tampered"  # type: ignore[misc]

    def test_anchor_rejects_insufficient_vectors(self):
        """Need ≥2 vectors for statistical significance."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)

        with pytest.raises(ValueError, match="≥2 vectors"):
            monitor.compute_anchor([[1.0, 2.0, 3.0]])

    def test_anchor_mean_and_variance(self):
        """Verify mean vector and variance trace are correctly computed."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)

        # Deterministic vectors
        vecs = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        anchor = monitor.compute_anchor(vecs)

        expected_mean = np.mean(vecs, axis=0)
        anchor_mean = np.frombuffer(anchor.mean_vector, dtype=np.float32)
        np.testing.assert_allclose(anchor_mean, expected_mean)

        expected_var_trace = float(np.sum(np.var(vecs, axis=0)))
        assert abs(anchor.variance_trace - expected_var_trace) < 1e-6

    def test_anchor_structural_proxies(self):
        """Verify that spectral gap, intrinsic dimension, and hubness are computed."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)

        vecs = _random_vectors(20, 8)
        anchor = monitor.compute_anchor(vecs)

        assert hasattr(anchor, "spectral_gap")
        assert hasattr(anchor, "intrinsic_dim")
        assert hasattr(anchor, "hubness")

        # Valid structural metrics shouldn't be NaN
        assert not np.isnan(anchor.spectral_gap)
        assert not np.isnan(anchor.intrinsic_dim)
        assert not np.isnan(anchor.hubness)
        assert anchor.intrinsic_dim > 0.0


# ---------------------------------------------------------------------------
# Anchor Validation
# ---------------------------------------------------------------------------


class TestAnchorValidation:
    def test_same_model_validates(self):
        """Same model_hash → anchor is valid."""
        encoder = _make_mock_encoder("stable_model_v1")
        monitor = TopologicalHealthMonitor(encoder)
        anchor = monitor.compute_anchor(_random_vectors(5, 8))

        assert monitor.validate_anchor(anchor) is True
        assert monitor.needs_recalibration(anchor) is False

    def test_different_model_invalidates(self):
        """Different model_hash → anchor is INVALID, forces recalibration."""
        encoder_v1 = _make_mock_encoder("model_v1")
        monitor_v1 = TopologicalHealthMonitor(encoder_v1)
        anchor = monitor_v1.compute_anchor(_random_vectors(5, 8))

        # Simulate model update
        encoder_v2 = _make_mock_encoder("model_v2")
        monitor_v2 = TopologicalHealthMonitor(encoder_v2)

        assert monitor_v2.validate_anchor(anchor) is False
        assert monitor_v2.needs_recalibration(anchor) is True


# ---------------------------------------------------------------------------
# Drift Measurement
# ---------------------------------------------------------------------------


class TestDriftMeasurement:
    def test_drift_requires_valid_anchor(self):
        """Measuring drift with an invalidated anchor raises AnchorInvalidError."""
        encoder_v1 = _make_mock_encoder("model_v1")
        monitor_v1 = TopologicalHealthMonitor(encoder_v1)
        anchor = monitor_v1.compute_anchor(_random_vectors(5, 8))

        # Model changed
        encoder_v2 = _make_mock_encoder("model_v2")
        monitor_v2 = TopologicalHealthMonitor(encoder_v2)

        with pytest.raises(AnchorInvalidError, match="Model hash mismatch"):
            monitor_v2.measure_drift(_random_vectors(5, 8), anchor)

    def test_zero_drift_on_same_vectors(self):
        """Identical vectors should produce ~zero drift."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)
        vectors = _random_vectors(20, 8)

        anchor = monitor.compute_anchor(vectors)
        drift = monitor.measure_drift(vectors, anchor)

        assert drift < 1e-5

    def test_nonzero_drift_on_shifted_vectors(self):
        """Shifted vectors should produce measurable drift."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)

        original = _random_vectors(20, 8, seed=1)
        anchor = monitor.compute_anchor(original)

        # Shift all vectors by a constant
        shifted = original + 0.5
        drift = monitor.measure_drift(shifted, anchor)

        assert drift > 0.1  # Significant drift

    def test_dimension_mismatch_raises(self):
        """Anchor from 8-dim vectors, measure with 16-dim → ValueError."""
        encoder = _make_mock_encoder()
        monitor = TopologicalHealthMonitor(encoder)

        anchor = monitor.compute_anchor(_random_vectors(5, 8))

        with pytest.raises(ValueError, match="Dimension mismatch"):
            monitor.measure_drift(_random_vectors(5, 16), anchor)


# ---------------------------------------------------------------------------
# Proxy Rotation
# ---------------------------------------------------------------------------


class TestProxyRotation:
    def test_proxy_rotation(self):
        """Verify the active proxy rotates every N checkpoints."""
        encoder = _make_mock_encoder()
        rotation_interval = 2
        monitor = TopologicalHealthMonitor(encoder, rotation_interval=rotation_interval)

        assert monitor.active_proxy == "spectral_gap"

        vectors = _random_vectors(20, 8)
        anchor = monitor.compute_anchor(vectors)

        # Call 1: check=1, modulus=1 != 0 -> no rotation
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "spectral_gap"

        # Call 2: check=2, modulus=0 -> rotation!
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "intrinsic_dim"

        # Call 3: check=3, modulus=1 -> no rotation
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "intrinsic_dim"

        # Call 4: check=4, modulus=0 -> rotation!
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "hubness"

        # Call 5: check=5, modulus=1 -> no rotation
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "hubness"

        # Call 6: check=6, modulus=0 -> rotation back to spectral_gap!
        monitor.measure_drift(vectors, anchor)
        assert monitor.active_proxy == "spectral_gap"


# ---------------------------------------------------------------------------
# SemanticMutator Write-Gate Integration
# ---------------------------------------------------------------------------


class TestMutatorWriteGate:
    @pytest.mark.asyncio
    async def test_mutator_skips_on_model_drift(self):
        """SemanticMutator must skip mutation batch when model_hash has drifted."""
        from unittest.mock import AsyncMock, patch

        from cortex.memory.semantic_ram import SemanticMutator

        store = MagicMock()
        store._lock = MagicMock()
        store._lock.__aenter__ = AsyncMock(return_value=None)
        store._lock.__aexit__ = AsyncMock(return_value=None)

        # Create anchor with model_v1
        anchor = TopologicalAnchor(
            mean_vector=np.zeros(8, dtype=np.float32).tobytes(),
            variance_trace=1.0,
            spectral_gap=0.5,
            intrinsic_dim=1.0,
            hubness=0.1,
            timestamp=time.time(),
            model_hash="model_v1",
            sample_size=10,
        )

        # Monitor thinks current model is v2 → drift!
        monitor = TopologicalHealthMonitor(_make_mock_encoder("model_v2"))

        mutator = SemanticMutator(store, health_monitor=monitor, anchor=anchor)

        batch = {"fact_1": ([[0.1] * 8], 20.0)}

        # This should skip the batch, not execute _mutate
        with patch.object(mutator, "_pool") as mock_pool:
            await mutator._apply_topological_shift(batch)
            # The threadpool executor should NOT have been called
            mock_pool.submit.assert_not_called()

    @pytest.mark.asyncio
    async def test_mutator_proceeds_without_monitor(self):
        """Without a health monitor, mutations proceed normally (backwards-compatible)."""
        from cortex.memory.semantic_ram import SemanticMutator

        store = MagicMock()
        # SemanticMutator without monitor should not gate
        mutator = SemanticMutator(store)
        assert mutator._health_monitor is None
        assert mutator._anchor is None
