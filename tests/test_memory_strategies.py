"""Tests for the 5 Neuroscience-inspired Memory Strategies.

Strategy 1: CMS — Continuous Memory System (frequency tiers)
Strategy 2: ART Gate — Adaptive Resonance (anti-duplication)
Strategy 3: Sparse Encoding — Mushroom Body inspired
Strategy 4: Silent Engrams — Dual-trace consolidation
Strategy 5: BIFT Router — Oscillatory retrieval bands
"""

import math
import time
from unittest.mock import AsyncMock

import pytest

from cortex.memory.consolidation import (
    EngramState,
    SilentEngram,
    SystemsConsolidator,
)
from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.frequency import (
    BIFTRouter,
    ContinuousMemorySystem,
    MemoryFrequency,
    RetrievalBand,
)
from cortex.memory.resonance import AdaptiveResonanceGate, cosine_similarity
from cortex.memory.sparse import MushroomBodyEncoder

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_vs():
    store = AsyncMock()
    store.search_similar = AsyncMock(return_value=[])
    store.scan_engrams = AsyncMock(return_value=[])
    return store


def _make_engram(
    content: str = "test",
    energy: float = 1.0,
    embedding: list[float] | None = None,
    **kwargs,
) -> CortexSemanticEngram:
    return CortexSemanticEngram(
        id=kwargs.get("id", f"e-{content}"),
        tenant_id="t1",
        project_id="p1",
        content=content,
        embedding=embedding or [0.1, 0.2, 0.3],
        energy_level=energy,
        **{k: v for k, v in kwargs.items() if k != "id"},
    )


# ─── Strategy 1: CMS Tests ──────────────────────────────────────────


class TestContinuousMemorySystem:
    def test_classify_hot_by_default(self):
        cms = ContinuousMemorySystem(vector_store=None)
        tier = cms.classify_tier(access_count=0, energy_level=1.0)
        assert tier == MemoryFrequency.HOT

    def test_classify_warm_after_accesses(self):
        cms = ContinuousMemorySystem(vector_store=None)
        tier = cms.classify_tier(access_count=10, energy_level=0.5)
        assert tier == MemoryFrequency.WARM

    def test_classify_cold_stable(self):
        cms = ContinuousMemorySystem(vector_store=None)
        tier = cms.classify_tier(access_count=50, energy_level=0.7)
        assert tier == MemoryFrequency.COLD

    def test_classify_permafrost_axiom(self):
        cms = ContinuousMemorySystem(vector_store=None)
        tier = cms.classify_tier(access_count=200, energy_level=0.9)
        assert tier == MemoryFrequency.PERMAFROST

    def test_demotion_on_energy_drop(self):
        cms = ContinuousMemorySystem(vector_store=None)
        # High accesses but low energy → cannot reach permafrost
        tier = cms.classify_tier(access_count=200, energy_level=0.2)
        assert tier != MemoryFrequency.PERMAFROST


# ─── Strategy 2: ART Gate Tests ──────────────────────────────────────


class TestAdaptiveResonanceGate:
    def test_cosine_similarity_identical(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_reset_when_no_neighbors(self, mock_vs):
        gate = AdaptiveResonanceGate(vector_store=mock_vs, rho=0.85)
        candidate = _make_engram("new fact")
        action, result = await gate.gate(candidate)
        assert action == "reset"
        assert result.id == candidate.id
        mock_vs.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_resonance_when_similar_exists(self, mock_vs):
        existing = _make_engram(
            "old fact",
            energy=0.6,
            embedding=[0.1, 0.2, 0.3],
            id="existing-1",
        )
        mock_vs.search_similar.return_value = [existing]

        gate = AdaptiveResonanceGate(vector_store=mock_vs, rho=0.8, ltp_boost=0.3)
        candidate = _make_engram("new fact", embedding=[0.1, 0.2, 0.3])
        action, result = await gate.gate(candidate)

        assert action == "resonance"
        assert result.energy_level == pytest.approx(0.9)  # 0.6 + 0.3


# ─── Strategy 3: Sparse Encoding Tests ───────────────────────────────


class TestMushroomBodyEncoder:
    def test_expansion_factor(self):
        encoder = MushroomBodyEncoder(expansion_factor=4, sparsity=0.05)
        inp = [0.1] * 100
        out = encoder.encode(inp)
        assert len(out) == 400  # 100 * 4

    def test_sparsity_enforcement(self):
        encoder = MushroomBodyEncoder(expansion_factor=4, sparsity=0.05)
        inp = [0.1 * (i + 1) for i in range(100)]
        out = encoder.encode(inp)

        active = sum(1 for v in out if v > 0.0)
        total = len(out)
        actual_sparsity = 1.0 - (active / total)

        # Should be ≈ 95% sparse (only 5% active)
        assert actual_sparsity >= 0.90

    def test_l2_normalized(self):
        encoder = MushroomBodyEncoder(expansion_factor=4, sparsity=0.05)
        inp = [0.5, 0.3, 0.8, 0.1]
        out = encoder.encode(inp)
        norm = math.sqrt(sum(v * v for v in out))
        assert norm == pytest.approx(1.0, abs=0.01)

    def test_empty_input(self):
        encoder = MushroomBodyEncoder()
        assert encoder.encode([]) == []


# ─── Strategy 4: Silent Engrams Tests ────────────────────────────────


class TestSilentEngrams:
    def test_initial_state_is_silent(self):
        silent = SilentEngram(
            tenant_id="t1",
            project_id="p1",
            content="silent memory",
            embedding=[0.1],
        )
        assert silent.state == EngramState.SILENT
        assert not silent.is_mature()

    def test_maturation_after_time(self):
        silent = SilentEngram(
            tenant_id="t1",
            project_id="p1",
            content="will mature",
            embedding=[0.1],
            energy_level=0.8,
            maturation_days=0.0,  # Instant maturation for test
        )
        # Force creation time to past
        object.__setattr__(silent, "created_at", time.time() - 86400)
        assert silent.is_mature()

    def test_contradiction_resets_maturation(self):
        silent = SilentEngram(
            tenant_id="t1",
            project_id="p1",
            content="contested",
            embedding=[0.1],
            energy_level=0.8,
            maturation_days=0.0,
        )
        object.__setattr__(silent, "created_at", time.time() - 86400)
        assert silent.is_mature()

        # Contradict → resets clock
        silent.contradict()
        assert not silent.is_mature()
        assert silent.contradiction_count == 1

    def test_tick_compute_in_memory(self):
        silent = SilentEngram(
            tenant_id="t1",
            project_id="p1",
            content="self-computing",
            embedding=[0.1],
            energy_level=0.8,
            maturation_days=0.0,
        )
        object.__setattr__(silent, "created_at", time.time() - 86400)

        # The engram decides its own fate
        new_state = silent.tick()
        assert new_state == EngramState.MATURED

    @pytest.mark.asyncio
    async def test_dual_store(self, mock_vs):
        consolidator = SystemsConsolidator(vector_store=mock_vs, maturation_days=3.0)
        engram = _make_engram("dual trace")
        active, silent = await consolidator.dual_store(engram)

        assert active.id == engram.id
        assert silent.state == EngramState.SILENT
        assert silent.active_twin_id == engram.id
        assert mock_vs.upsert.call_count == 2  # active + silent


# ─── Strategy 5: BIFT Router Tests ──────────────────────────────────


class TestBIFTRouter:
    def test_short_query_gamma(self):
        band = BIFTRouter.classify_query("error fix")
        assert band == RetrievalBand.GAMMA

    def test_standard_query_beta(self):
        band = BIFTRouter.classify_query("how does the authentication system handle token refresh")
        assert band == RetrievalBand.BETA

    def test_cross_project_theta(self):
        band = BIFTRouter.classify_query("auth pattern", is_cross_project=True)
        assert band == RetrievalBand.THETA

    def test_axiom_delta(self):
        band = BIFTRouter.classify_query("zero trust principle", is_axiom_lookup=True)
        assert band == RetrievalBand.DELTA

    def test_config_retrieval(self):
        config = BIFTRouter.get_config(RetrievalBand.GAMMA)
        assert config.max_results == 5
        assert config.min_energy == 0.6
