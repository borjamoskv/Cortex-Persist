# [C5-REAL] Exergy-Maximized
"""
Unit tests for vector obfuscation.
Designed by Borja Moskv.
"""

from __future__ import annotations

import os
import math
import numpy as np
import pytest

from babylon60.embeddings.obfuscation import obfuscate_vector, derive_pad_vector


def cosine_similarity(v1: list[float] | np.ndarray, v2: list[float] | np.ndarray) -> float:
    arr1 = np.array(v1, dtype=np.float32)
    arr2 = np.array(v2, dtype=np.float32)
    dot = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


def test_obfuscation_disabled_by_default(monkeypatch):
    monkeypatch.setenv("CORTEX_OBFUSCATE_EMBEDDINGS", "0")
    vec = [0.1, 0.2, 0.3, 0.4]
    obf = obfuscate_vector(vec, tenant_id="default", project="test")
    assert obf == vec


def test_obfuscation_enabled(monkeypatch):
    monkeypatch.setenv("CORTEX_OBFUSCATE_EMBEDDINGS", "1")
    monkeypatch.setenv("CORTEX_OBFUSCATION_PAD_SCALE", "0.5")

    vec = [0.1, 0.2, 0.3, 0.4]
    obf = obfuscate_vector(vec, tenant_id="default", project="test")

    assert len(obf) == len(vec)
    assert obf != vec

    # Same context should produce identical obfuscated vector
    obf_same = obfuscate_vector(vec, tenant_id="default", project="test")
    assert obf_same == obf

    # Different project should produce different obfuscated vector
    obf_diff_proj = obfuscate_vector(vec, tenant_id="default", project="other")
    assert obf_diff_proj != obf

    # Different tenant should produce different obfuscated vector
    obf_diff_tenant = obfuscate_vector(vec, tenant_id="tenant2", project="test")
    assert obf_diff_tenant != obf


def test_vector_obfuscation_cosine_similarity_preservation(monkeypatch):
    monkeypatch.setenv("CORTEX_OBFUSCATE_EMBEDDINGS", "1")
    # Using a small pad scale (e.g. 0.05) preserves similarity ranking perfectly
    monkeypatch.setenv("CORTEX_OBFUSCATION_PAD_SCALE", "0.05")

    # Create 3 vectors: query, match, and non-match
    np.random.seed(42)
    q = np.random.randn(384)
    q = q / np.linalg.norm(q)

    m1 = q + np.random.randn(384) * 0.1
    m1 = m1 / np.linalg.norm(m1)

    m2 = np.random.randn(384)
    m2 = m2 / np.linalg.norm(m2)

    # Raw similarities
    sim_raw_match = cosine_similarity(q, m1)
    sim_raw_other = cosine_similarity(q, m2)

    # Ensure raw match is closer
    assert sim_raw_match > sim_raw_other

    # Obfuscate all vectors with the same project context
    q_obf = obfuscate_vector(q.tolist(), tenant_id="default", project="cortex")
    m1_obf = obfuscate_vector(m1.tolist(), tenant_id="default", project="cortex")
    m2_obf = obfuscate_vector(m2.tolist(), tenant_id="default", project="cortex")

    sim_obf_match = cosine_similarity(q_obf, m1_obf)
    sim_obf_other = cosine_similarity(q_obf, m2_obf)

    # The rank order must be preserved: match similarity is higher than other similarity
    assert sim_obf_match > sim_obf_other

    # Under a small pad scale, similarity deviation should be minimal (norm drift check)
    deviation = abs(sim_raw_match - sim_obf_match)
    assert deviation < 0.05


@pytest.mark.asyncio
async def test_cortex_engine_end_to_end_obfuscation(monkeypatch, tmp_path):
    import json

    monkeypatch.setenv("CORTEX_OBFUSCATE_EMBEDDINGS", "1")
    monkeypatch.setenv("CORTEX_OBFUSCATION_PAD_SCALE", "0.05")

    # Unblock tests from thermodynamic enforcement
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")

    from babylon60.engine import CortexEngine

    db = str(tmp_path / "test_obfuscate.db")
    engine = CortexEngine(db_path=db, auto_embed=True)
    await engine.init_db()

    try:
        fact_id = await engine.store(
            project="test_proj",
            content="Sovereign AI encryption layer",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        assert fact_id > 0

        # Verify it was stored with an embedding
        async with engine.session() as conn:
            async with conn.execute(
                "SELECT embedding FROM fact_embeddings WHERE fact_id = ?", (fact_id,)
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                stored_emb = np.frombuffer(row[0], dtype=np.float32).tolist()
                assert len(stored_emb) == 384

        # Search for it
        results = await engine.search(query="AI encryption layer", project="test_proj", top_k=1)

        assert len(results) > 0
        assert "Sovereign AI" in results[0].content
    finally:
        await engine.close()
