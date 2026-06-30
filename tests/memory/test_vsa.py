# [C5-REAL] Exergy-Maximized
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from babylon60.memory.vsa import (
    random_bipolar,
    bind,
    bundle,
    hamming_distance,
    cosine_similarity,
    TextEncoder,
    KanervaSDM,
    SwarmMemory,
    VSAPipelineBridge,
    DIMENSION,
)


def test_random_bipolar():
    """Validates that random_bipolar generates a vector of correct dimension and values."""
    dim = 100
    vec = random_bipolar(dim)
    assert len(vec) == dim
    assert all(x in [0, 1] for x in vec)


def test_bind():
    """Validates XOR binding and its self-inverse property."""
    a = [0, 1, 0, 1]
    b = [1, 1, 0, 0]
    bound = bind(a, b)
    assert bound == [1, 0, 0, 1]
    # Self-inverse: bind(bind(a, b), b) == a
    assert bind(bound, b) == a


def test_bundle():
    """Validates majority-rule bundling for multiple vectors."""
    v1 = [1, 1, 0, 0]
    v2 = [1, 0, 1, 0]
    v3 = [1, 1, 1, 1]
    # Majority:
    # bit 0: 1, 1, 1 -> 1
    # bit 1: 1, 0, 1 -> 1
    # bit 2: 0, 1, 1 -> 1
    # bit 3: 0, 0, 1 -> 0
    bundled = bundle([v1, v2, v3])
    assert bundled == [1, 1, 1, 0]

    # Edge case: empty list
    assert bundle([]) == [0] * DIMENSION


def test_hamming_distance():
    """Validates Hamming distance calculation."""
    a = [0, 1, 0, 1]
    b = [1, 1, 0, 0]
    # Differences at index 0 and 3
    assert hamming_distance(a, b) == 2
    assert hamming_distance(a, a) == 0


def test_cosine_similarity():
    """Validates cosine similarity for binary vectors mapped to {-1, 1}."""
    a = [1, 1, 0, 0]  # -> [1, 1, -1, -1]
    b = [1, 1, 0, 0]  # -> [1, 1, -1, -1]
    # dot = 1*1 + 1*1 + (-1)*(-1) + (-1)*(-1) = 4. dim=4. sim = 4/4 = 1.0
    assert cosine_similarity(a, b) == 1.0

    c = [0, 0, 1, 1]  # -> [-1, -1, 1, 1]
    # dot = 1*-1 + 1*-1 + -1*1 + -1*1 = -4. sim = -4/4 = -1.0
    assert cosine_similarity(a, c) == -1.0

    d = [1, 0, 1, 0]  # -> [1, -1, 1, -1]
    # dot = 1*1 + 1*-1 + -1*1 + -1*-1 = 1 - 1 - 1 + 1 = 0. sim = 0.0
    assert cosine_similarity(a, d) == 0.0

    assert cosine_similarity([], []) == 0.0


def test_text_encoder():
    """Validates text encoding into hypervectors."""
    encoder = TextEncoder(dim=100, ngram_size=3)
    vec1 = encoder.encode("hello")
    vec2 = encoder.encode("hello")
    vec3 = encoder.encode("world")

    assert len(vec1) == 100
    assert vec1 == vec2
    assert vec1 != vec3

    # Test empty string
    assert encoder.encode("") == [0] * 100

    # Test very short string (shorter than ngram_size)
    vec_short = encoder.encode("hi")
    assert any(x != 0 for x in vec_short)


def test_kanerva_sdm():
    """Validates Kanerva SDM write and read operations."""
    dim = 100
    sdm = KanervaSDM(dim=dim, num_locations=50, activation_radius=45)
    sdm.initialize()

    address = random_bipolar(dim, seed=42)
    data = random_bipolar(dim, seed=43)

    # Write
    activated_count = sdm.write(address, data)
    assert activated_count >= 0

    # Read
    reconstructed = sdm.read(address)
    assert len(reconstructed) == dim

    # Similarity should be high if activated
    if activated_count > 0:
        sim = cosine_similarity(data, reconstructed)
        assert sim > 0


def test_kanerva_sdm_decay():
    """Validates Ebbinghaus decay in SDM."""
    dim = 100
    sdm = KanervaSDM(dim=dim, num_locations=50, activation_radius=100)  # Ensure activation
    address = random_bipolar(dim)
    data = [1] * dim
    sdm.write(address, data)

    initial_stats = sdm.stats
    assert initial_stats["active_locations"] > 0

    affected = sdm.apply_decay(rate=0.5)
    assert affected > 0

    # After heavy decay, read might return zeros or different values
    reconstructed = sdm.read(address)
    assert len(reconstructed) == dim


def test_swarm_memory(tmp_path):
    """Validates SwarmMemory record, recall and persistence."""
    # Override PERSISTENCE_DIR by monkeypatching if possible,
    # but SwarmMemory uses it at init to set _persistence_path.

    agent_id = "test_agent"
    # We'll manually set the persistence path to avoid writing to ~/.cortex
    mem = SwarmMemory(agent_id=agent_id, dim=100)
    mem._persistence_path = tmp_path / f"{agent_id}.vsa"

    rid = mem.record("This is a test memory", tags=["test", "vsa"])
    assert rid is not None

    results = mem.recall("test memory")
    assert len(results) > 0
    assert results[0]["id"] == rid
    assert "test" in results[0]["tags"]

    # Persistence
    integrity_hash = mem.persist()
    assert integrity_hash is not None
    assert mem._persistence_path.exists()

    # Loading
    mem2 = SwarmMemory(agent_id=agent_id, dim=100)
    mem2._persistence_path = tmp_path / f"{agent_id}.vsa"
    loaded_count = mem2.load()
    assert loaded_count == 1
    assert rid in mem2._records
    assert mem2._records[rid].content == "This is a test memory"


def test_swarm_memory_consolidate():
    """Validates memory consolidation and pruning."""
    mem = SwarmMemory(agent_id="test_consolidate", dim=100)
    # Write a memory
    mem.record("Persistent memory")

    # Apply massive decay
    mem.consolidate(decay_rate=1.0)

    # Should be pruned as it won't recall properly
    assert len(mem._records) == 0


def test_vsa_pipeline_bridge(tmp_path):
    """Validates VSAPipelineBridge operations."""
    bridge = VSAPipelineBridge(agent_id="bridge_test")
    bridge._memory._persistence_path = tmp_path / "bridge_test.vsa"
    bridge._memory._dim = 100  # Use smaller dim for test
    bridge._memory._encoder = TextEncoder(dim=100)
    bridge._memory._sdm = KanervaSDM(dim=100)

    rid = bridge.ingest("Bridge data", tags=["bridge"])
    assert rid is not None

    results = bridge.query("Bridge data")
    assert len(results) > 0
    assert results[0]["content"] == "Bridge data"

    h = bridge.persist()
    assert h is not None
    assert bridge.stats["records"] == 1
