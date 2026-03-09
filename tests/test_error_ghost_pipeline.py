"""Tests for ErrorGhostPipeline — Ω₅ Antifragile Autopersistence."""

from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline


@pytest.fixture(autouse=True)
def fresh_pipeline():
    """Reset the singleton pipeline before each test."""
    pipeline = ErrorGhostPipeline()
    pipeline.reset()
    # Reset singleton so each test gets fresh state
    ErrorGhostPipeline._instance = None
    yield
    pipeline = ErrorGhostPipeline()
    pipeline.reset()


class TestPrepare:
    """Test content/meta preparation from errors."""

    def test_prepare_builds_content_with_source_and_type(self):
        pipeline = ErrorGhostPipeline()
        try:
            raise ValueError("test error 42")
        except ValueError as e:
            content, content_hash, meta = pipeline._prepare(
                e, "daemon:SiteMonitor", None
            )

        assert "AUTO-GHOST [daemon:SiteMonitor]" in content
        assert "ValueError" in content
        assert "test error 42" in content
        assert len(content_hash) == 16
        assert meta["error_type"] == "ValueError"
        assert meta["source"] == "daemon:SiteMonitor"
        assert meta["pipeline"] == "error_ghost_v1"

    def test_prepare_includes_extra_meta(self):
        pipeline = ErrorGhostPipeline()
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            _, _, meta = pipeline._prepare(
                e, "test:source", {"custom_key": "custom_val"}
            )

        assert meta["custom_key"] == "custom_val"
        assert meta["error_type"] == "RuntimeError"


class TestDedup:
    """Test content-hash dedup ring buffer."""

    def test_same_error_deduped(self):
        pipeline = ErrorGhostPipeline()
        try:
            raise ValueError("identical")
        except ValueError as e:
            _, hash1, _ = pipeline._prepare(e, "src", None)

        # First emission: not suppressed
        assert not pipeline._should_suppress(hash1, "src")
        pipeline._record_emission(hash1, "src", 1)

        # Second emission with same hash: suppressed
        assert pipeline._should_suppress(hash1, "src")
        assert pipeline.stats["total_deduped"] == 1

    def test_different_errors_not_deduped(self):
        pipeline = ErrorGhostPipeline()

        # Different error types produce different hashes
        try:
            raise ValueError("error A")
        except ValueError as e:
            _, hash_a, _ = pipeline._prepare(e, "src_a", None)

        try:
            raise RuntimeError("error B")
        except RuntimeError as e:
            _, hash_b, _ = pipeline._prepare(e, "src_b", None)

        assert hash_a != hash_b
        assert not pipeline._should_suppress(hash_a, "src_a")
        pipeline._record_emission(hash_a, "src_a", 1)
        assert not pipeline._should_suppress(hash_b, "src_b")

    def test_ring_buffer_eviction(self):
        pipeline = ErrorGhostPipeline()

        # Fill buffer beyond capacity to trigger eviction
        for i in range(70):
            h = f"hash_{i:04d}"
            pipeline._record_emission(h, f"src_{i}", i)

        # Early hashes should have been evicted
        assert pipeline.stats["dedup_window_size"] == 64
        assert not pipeline._should_suppress("hash_0000", "new_src")


class TestRateLimit:
    """Test per-source rate limiting."""

    def test_same_source_rate_limited(self):
        pipeline = ErrorGhostPipeline()

        # First emission for this source
        assert not pipeline._should_suppress("hash_x", "source_alpha")
        pipeline._record_emission("hash_x", "source_alpha", 1)

        # Different hash but same source within rate window
        assert pipeline._should_suppress("hash_y", "source_alpha")
        assert pipeline.stats["total_rate_limited"] == 1

    def test_different_sources_not_rate_limited(self):
        pipeline = ErrorGhostPipeline()

        assert not pipeline._should_suppress("hash_1", "source_A")
        pipeline._record_emission("hash_1", "source_A", 1)

        # Different source — not rate limited
        assert not pipeline._should_suppress("hash_2", "source_B")


class TestCapture:
    """Test the full capture flow."""

    @pytest.mark.asyncio
    async def test_capture_stores_ghost_fact(self):
        pipeline = ErrorGhostPipeline()

        mock_engine = MagicMock()
        mock_engine.store = AsyncMock(return_value=42)

        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=42,
        ):
            try:
                raise ValueError("capture test")
            except ValueError as e:
                fact_id = await pipeline.capture(
                    e, source="test:capture", project="TEST"
                )

        assert fact_id == 42
        assert pipeline.stats["total_captured"] == 1

    @pytest.mark.asyncio
    async def test_capture_returns_none_on_dedup(self):
        pipeline = ErrorGhostPipeline()

        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=1,
        ):
            try:
                raise ValueError("same error")
            except ValueError as e:
                first = await pipeline.capture(e, source="s", project="P")
                second = await pipeline.capture(e, source="s", project="P")

        assert first == 1
        assert second is None


class TestStats:
    """Test pipeline health stats."""

    def test_stats_initial(self):
        pipeline = ErrorGhostPipeline()
        s = pipeline.stats
        assert s["total_captured"] == 0
        assert s["total_deduped"] == 0
        assert s["total_rate_limited"] == 0
        assert s["dedup_window_size"] == 0

    def test_reset_clears_all(self):
        pipeline = ErrorGhostPipeline()
        pipeline._record_emission("h", "s", 1)
        pipeline.reset()
        s = pipeline.stats
        assert s["total_captured"] == 0
        assert s["dedup_window_size"] == 0
