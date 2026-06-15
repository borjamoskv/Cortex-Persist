# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cortex.extensions.daemon.translator import PartitionedAsyncSignalBus, ShardedTranslationDaemon
from cortex.extensions.signals.models import Signal


@pytest.mark.asyncio
async def test_partitioned_signal_bus_initialization():
    """Verify that PartitionedAsyncSignalBus starts correctly and matches shard subset."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create sharded bus with 4 shards, only worker 0 active on shard 1 and 3
        bus = PartitionedAsyncSignalBus(tmp_dir, num_shards=4, active_shards=[1, 3])
        await bus.initialize()

        assert len(bus._shards) == 4
        assert bus.active_shards == [1, 3]
        await bus.close()


@pytest.mark.asyncio
async def test_translation_daemon_flow():
    """Verify that ShardedTranslationDaemon processes translation requests and emits completions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        daemon = ShardedTranslationDaemon(
            shards_dir=tmp_dir,
            worker_id="test_worker_1",
            shard_indices=[0],
            poll_interval_s=0.1,
        )

        # Mock the translate_text method to avoid hitting the actual Gemini API in tests
        daemon.translate_text = AsyncMock(return_value="Hello World")

        # Initialize bus and emit a request directly into shard 0
        await daemon.bus.initialize()
        correlation_id = "test-corr-123"

        # Find a routing key that hashes to shard index 0
        routing_key = "some_key"
        for i in range(100):
            key = f"key_{i}"
            if daemon.bus._get_shard_index(key) == 0:
                routing_key = key
                break

        await daemon.bus.emit(
            event_type="translation:request",
            payload={
                "text": "Hola Mundo",
                "target_lang": "en",
                "source_lang": "es",
                "correlation_id": correlation_id,
            },
            source="test_client",
            routing_key=routing_key,
        )

        # Force poll directly
        polled = await daemon.bus.poll_partition(
            event_type="translation:request",
            consumer=daemon.worker_id,
            limit=1,
        )
        assert len(polled) == 1
        assert polled[0].payload["text"] == "Hola Mundo"

        # Process the request
        await daemon.process_request(polled[0])

        # Verify translation completion signal was emitted using correlation_id as routing key
        history = await daemon.bus.history(routing_key=correlation_id)
        assert len(history) >= 1

        completed_sig = next((s for s in history if s.event_type == "translation:completed"), None)
        assert completed_sig is not None
        assert completed_sig.payload["translated_text"] == "Hello World"
        assert completed_sig.payload["correlation_id"] == correlation_id
        assert completed_sig.payload["worker_id"] == "test_worker_1"
        assert completed_sig.payload["offline_fallback"] is False

        await daemon.bus.close()


@pytest.mark.asyncio
async def test_translation_fallback():
    """Verify three-tier fallback behaves correctly when LLM API is unavailable."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        daemon = ShardedTranslationDaemon(
            shards_dir=tmp_dir,
            worker_id="test_worker_fallback",
            shard_indices=[0],
            poll_interval_s=0.1,
        )

        # Force Gemini API client lookup failure and LLMManager unavailability
        with (
            patch.object(daemon, "_get_client", side_effect=RuntimeError("No API Key")),
            patch("cortex.extensions.llm.manager.LLMManager._get_provider", return_value=None),
        ):
            # Translate text using fallback
            res = await daemon.translate_text("Hola Mundo", "en", "es")
            assert "[OFFLINE FALLBACK]:" in res
            assert "hello world" in res.lower()
