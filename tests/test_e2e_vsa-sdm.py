# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from legacy_research.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from legacy_research.pipeline.orchestrator import CortexOrchestrator
from legacy_research.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from legacy_research.router.router import AgentRouter, AgentCapability
from legacy_research.context.assembler import ContextAssembler
from legacy_research.delivery.manager import DeliveryManager


# ── VSA-SDM Tests ──


class TestVSAAlgebra:
    """Test MAP-B binary vector algebra."""

    def test_bind_self_inverse(self):
        """XOR bind is its own inverse."""
        from legacy_research.memory.vsa import bind, random_bipolar

        a = random_bipolar(500, seed=1)
        b = random_bipolar(500, seed=2)
        c = bind(a, b)
        recovered = bind(c, b)
        assert a == recovered

    def test_bundle_preserves_constituents(self):
        """Bundle is closer to constituents than random vectors."""
        from legacy_research.memory.vsa import bundle, cosine_similarity, random_bipolar

        v1 = random_bipolar(500, seed=10)
        v2 = random_bipolar(500, seed=20)
        sup = bundle([v1, v2])
        sim_constituent = cosine_similarity(sup, v1)
        sim_random = cosine_similarity(sup, random_bipolar(500, seed=99))
        assert sim_constituent > sim_random

    def test_hamming_distance(self):
        """Hamming distance of identical vectors is 0."""
        from legacy_research.memory.vsa import hamming_distance, random_bipolar

        v = random_bipolar(500, seed=42)
        assert hamming_distance(v, v) == 0
        assert hamming_distance(v, [1 - x for x in v]) == 500


class TestTextEncoder:
    """Test text-to-hypervector encoding."""

    def test_related_texts_higher_similarity(self):
        """Related texts have higher cosine similarity than unrelated."""
        from legacy_research.memory.vsa import TextEncoder, cosine_similarity

        enc = TextEncoder(dim=1000)
        h1 = enc.encode("smart contract vulnerability")
        h2 = enc.encode("smart contract exploit")
        h3 = enc.encode("banana smoothie recipe")
        sim_related = cosine_similarity(h1, h2)
        sim_unrelated = cosine_similarity(h1, h3)
        assert sim_related > sim_unrelated

    def test_empty_text(self):
        """Empty text returns zero vector."""
        from legacy_research.memory.vsa import TextEncoder

        enc = TextEncoder(dim=100)
        v = enc.encode("")
        assert all(x == 0 for x in v)


class TestSwarmMemory:
    """Test per-agent associative memory."""

    def test_record_and_recall(self):
        """Record memories and recall by similarity."""
        from legacy_research.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_mem", dim=1000)
        mem.record("DeFi flash loan attack vector", tags=["security"])
        mem.record("Reentrancy vulnerability", tags=["security"])
        mem.record("Weather is rainy in Bilbao", tags=["misc"])

        results = mem.recall("flash loan exploit", top_k=3)
        assert len(results) > 0
        assert "flash" in results[0]["content"].lower() or "loan" in results[0]["content"].lower()

    def test_consolidation(self):
        """Consolidation applies decay without crashing."""
        from legacy_research.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_decay", dim=500)
        mem.record("test memory 1")
        mem.record("test memory 2")
        pruned = mem.consolidate(decay_rate=0.01)
        assert isinstance(pruned, int)

    def test_persistence(self, tmp_path):
        """Persist and reload memories."""
        from legacy_research.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_persist", dim=500)
        mem._persistence_path = tmp_path / "test.vsa"
        mem.record("persistent memory", record_id="p1")
        hash_val = mem.persist()
        assert len(hash_val) == 64  # SHA-256

        mem2 = SwarmMemory(agent_id="test_persist", dim=500)
        mem2._persistence_path = tmp_path / "test.vsa"
        loaded = mem2.load()
        assert loaded == 1
        assert "p1" in mem2._records


class TestVSAPipelineBridge:
    """Test VSA bridge for ContextAssembler."""

    def test_bridge_query(self):
        """Bridge.query returns results in expected format."""
        from legacy_research.memory.vsa import SwarmMemory, VSAPipelineBridge

        bridge = VSAPipelineBridge.__new__(VSAPipelineBridge)
        bridge._memory = SwarmMemory(agent_id="bridge_test", dim=1000)
        bridge._memory.record("Oracle manipulation attack", tags=["vuln"])
        bridge._memory.record("Cross-chain bridge exploit", tags=["vuln"])

        results = bridge.query("oracle vulnerability", top_k=2)
        assert len(results) > 0
        assert "content" in results[0]
        assert "similarity" in results[0]

    def test_bridge_ingest(self):
        """Bridge.ingest stores and returns record ID."""
        from legacy_research.memory.vsa import SwarmMemory, VSAPipelineBridge

        bridge = VSAPipelineBridge.__new__(VSAPipelineBridge)
        bridge._memory = SwarmMemory(agent_id="ingest_test", dim=500)

        rid = bridge.ingest("test knowledge item", record_id="ki-001")
        assert rid == "ki-001"
        assert bridge.stats["records"] == 1
