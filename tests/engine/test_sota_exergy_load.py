# [C5-REAL] Exergy-Maximized
"""
SOTA Exergic Load Testing Suite.
Validates the structural integrity and high-throughput execution of the 5 injected SOTA architectures:
1. RiM (Latent Reasoning)
2. LLMSurgeon (Data Mixture Surgery)
3. SchGen (Semantic PCB Routing)
4. VisAnomReasoner (VLM Anomaly Detection)
5. VideoMLA (Latent KV Cache Compression)
"""

import time
import pytest
from cortex.engine.uncategorized.data_surgery import DataSurgeon
from cortex_extensions.hardware.schgen_router import SchGenRouter
from cortex.engine.meta.vision_reasoner import VisAnomReasoner
from cortex.engine.uncategorized.video_mla_cache import VideoMLACache
from cortex.engine.flow.rim_latent_blocks import ReasoningInMemoryEngine


@pytest.mark.asyncio
async def test_rim_latent_blocks_load():
    engine = ReasoningInMemoryEngine(blocks=4, tokens_per_block=16)

    start_time = time.monotonic()
    payload = "Evaluate market exergy."

    for _ in range(1000):
        res = engine.apply_latent_reasoning(payload)
        assert "[LATENT_COMPUTE_START]" in res

    duration = time.monotonic() - start_time
    audit = engine.audit_exergy()

    assert audit["autoregressive_tokens_saved_per_pass"] == 64
    assert duration < 15.0


@pytest.mark.asyncio
async def test_llmsurgeon_load():
    surgeon = DataSurgeon(sensitivity=0.85)
    dataset = [f"data_chunk_{i}_simulation" for i in range(10000)]

    start_time = time.monotonic()
    audit = surgeon.audit_mixture(dataset)
    pruned = surgeon.execute_surgery(dataset, audit)
    duration = time.monotonic() - start_time

    assert len(pruned) <= len(dataset)
    assert audit.entropy_score > 0
    assert duration < 15.0


@pytest.mark.asyncio
async def test_schgen_load():
    router = SchGenRouter(max_density=0.95)
    components = [f"COMP_{i}" for i in range(1000)]
    semantic_intent = " ".join(["create power array", "route MCU SPI", "deploy sensors"] * 50)

    start_time = time.monotonic()
    netlist = router.generate_netlist(semantic_intent, components)
    duration = time.monotonic() - start_time

    assert len(netlist.nodes) == 1000
    assert duration < 15.0


@pytest.mark.asyncio
async def test_visanom_reasoner_load():
    reasoner = VisAnomReasoner(window_size=50, anomaly_threshold=0.6)
    start_time = time.monotonic()

    anomalies_detected = 0
    for i in range(1000):
        # Alternate every frame to maximize sequential entropy
        frame_hex = "f" * 64 if i % 2 == 0 else "0" * 64
        rationale = reasoner.process_frame(timestamp=float(i), frame_embedding_hex=frame_hex)
        if rationale and rationale.is_anomalous:
            anomalies_detected += 1

    duration = time.monotonic() - start_time
    assert anomalies_detected > 0
    assert duration < 15.0


@pytest.mark.asyncio
async def test_video_mla_cache_load():
    cache = VideoMLACache(compression_factor=8)
    start_time = time.monotonic()

    for i in range(5000):
        key = f"key_{i}"
        val = "V" * 1024
        cache.store_kv(frame_idx=i, key_tensor=key, value_tensor=val)

    stats = cache.get_cache_stats()

    for i in range(100):
        retrieved = cache.retrieve_kv(frame_idx=i, key_tensor=f"key_{i}")
        assert retrieved is not None
        assert retrieved.compression_ratio >= 1.0

    duration = time.monotonic() - start_time
    assert stats["total_items"] == 5000
    assert duration < 15.0
