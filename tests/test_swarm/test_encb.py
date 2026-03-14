"""
Tests for the Epistemic Noise Chaos Benchmark (ENCB).

Validates:
1. Chaos generator produces correct event types and counts.
2. Ground truth is correctly tracked.
3. Baseline RAG stores everything without filtering.
4. Byzantine detection works at the structural level.
"""

from __future__ import annotations

import asyncio

import pytest

from benchmarks.encb_baseline_rag import BaselineRAG
from benchmarks.encb_chaos_generator import (
    ChaosModality,
    EpisodicSpamGenerator,
    EpistemicChaosOrchestrator,
    TemporalContradictionGenerator,
    TransitiveBreakageGenerator,
)


# ── Temporal Contradiction Tests ───────────────────────────────────────────


class TestTemporalContradiction:
    def test_setup_creates_ground_truth(self):
        gen = TemporalContradictionGenerator(
            num_propositions=5, num_agents=3, byzantine_ratio=0.3
        )
        gt = gen.setup()

        assert gt.total_propositions == 5
        assert len(gt.signal_facts) == 5
        assert all(isinstance(v, bool) for v in gt.propositions.values())

    def test_generate_produces_events(self):
        gen = TemporalContradictionGenerator(
            num_propositions=3, num_agents=2, byzantine_ratio=0.5
        )
        gen.setup()
        events = gen.generate(num_rounds=5)

        # 3 propositions × 2 agents × 5 rounds = 30 events
        assert len(events) == 30
        assert all(e.modality == ChaosModality.TEMPORAL_CONTRADICTION for e in events)

    def test_byzantine_agents_exist(self):
        gen = TemporalContradictionGenerator(
            num_propositions=2, num_agents=5, byzantine_ratio=0.4
        )
        gen.setup()
        events = gen.generate(num_rounds=2)

        byzantine_events = [e for e in events if e.meta.get("is_byzantine")]
        honest_events = [e for e in events if not e.meta.get("is_byzantine")]

        assert len(byzantine_events) > 0
        assert len(honest_events) > 0

    def test_events_have_unique_ids(self):
        gen = TemporalContradictionGenerator(
            num_propositions=2, num_agents=2, byzantine_ratio=0.5
        )
        gen.setup()
        events = gen.generate(num_rounds=3)

        ids = [e.event_id for e in events]
        assert len(ids) == len(set(ids)), "Event IDs must be unique"


# ── Transitive Breakage Tests ─────────────────────────────────────────────


class TestTransitiveBreakage:
    def test_setup_creates_chains(self):
        gen = TransitiveBreakageGenerator(chain_depth=5, num_chains=3, p_break=0.5)
        gt = gen.setup()

        # 3 chains × 5 depth = 15 propositions
        assert gt.total_propositions == 15
        assert len(gt.entails_chains) == 3
        assert all(len(c) == 5 for c in gt.entails_chains)

    def test_generate_has_establish_and_break_phases(self):
        gen = TransitiveBreakageGenerator(chain_depth=4, num_chains=2, p_break=1.0)
        gen.setup()
        events = gen.generate()

        establish_events = [
            e for e in events if e.meta.get("phase") == "establish"
        ]
        break_events = [
            e for e in events if e.meta.get("phase") == "break"
        ]

        # 2 chains × 4 depth = 8 establish events
        assert len(establish_events) == 8
        # p_break=1.0 → all 2 roots broken
        assert len(break_events) == 2

    def test_zero_break_probability(self):
        gen = TransitiveBreakageGenerator(chain_depth=3, num_chains=3, p_break=0.0)
        gen.setup()
        events = gen.generate()

        break_events = [e for e in events if e.meta.get("phase") == "break"]
        assert len(break_events) == 0


# ── Episodic Spam Tests ────────────────────────────────────────────────────


class TestEpisodicSpam:
    def test_setup_creates_signal_facts(self):
        gen = EpisodicSpamGenerator(rho_noise=5.0, num_signal_facts=4)
        gt = gen.setup()

        assert gt.total_propositions == 4
        assert len(gt.signal_facts) == 4

    def test_generate_signal_to_noise_ratio(self):
        gen = EpisodicSpamGenerator(rho_noise=10.0, num_signal_facts=5)
        gen.setup()
        events = gen.generate()

        signal_events = [e for e in events if e.meta.get("is_signal")]
        noise_events = [e for e in events if not e.meta.get("is_signal")]

        assert len(signal_events) == 5
        assert len(noise_events) == 50  # 5 × 10.0
        assert len(events) == 55

    def test_spam_is_related_to_signal(self):
        gen = EpisodicSpamGenerator(rho_noise=2.0, num_signal_facts=3)
        gen.setup()
        events = gen.generate()

        noise_events = [e for e in events if not e.meta.get("is_signal")]
        for noise in noise_events:
            # Each spam event references a source signal
            assert "source_signal" in noise.meta


# ── Orchestrator Tests ─────────────────────────────────────────────────────


class TestEpistemicChaosOrchestrator:
    def test_setup_all_creates_three_ground_truths(self):
        orch = EpistemicChaosOrchestrator(
            num_propositions=3, num_agents=2, num_chains=2,
            chain_depth=3, num_signal_facts=3, rho_noise=2.0,
        )
        gts = orch.setup_all()

        assert len(gts) == 3
        assert ChaosModality.TEMPORAL_CONTRADICTION in gts
        assert ChaosModality.TRANSITIVE_BREAKAGE in gts
        assert ChaosModality.EPISODIC_SPAM in gts

    def test_generate_all_produces_events(self):
        orch = EpistemicChaosOrchestrator(
            num_propositions=2, num_agents=2, num_chains=2,
            chain_depth=3, num_signal_facts=2, rho_noise=2.0,
        )
        orch.setup_all()
        events = orch.generate_all(temporal_rounds=3)

        assert len(events) == 3
        total = orch.total_events(events)
        assert total > 0

        # Temporal: 2 propositions × 2 agents × 3 rounds = 12
        assert len(events[ChaosModality.TEMPORAL_CONTRADICTION]) == 12


# ── Baseline RAG Tests ─────────────────────────────────────────────────────


class TestBaselineRAG:
    @pytest.fixture
    def rag(self) -> BaselineRAG:
        return BaselineRAG()

    @pytest.mark.asyncio
    async def test_store_appends_everything(self, rag: BaselineRAG):
        await rag.store("fact 1")
        await rag.store("fact 1")  # Duplicate
        await rag.store("fact 2")

        assert rag.total_facts == 3  # No dedup!
        assert rag.unique_facts == 2

    @pytest.mark.asyncio
    async def test_search_returns_results(self, rag: BaselineRAG):
        await rag.store("CORTEX uses SHA-256 hash chains")
        await rag.store("Byzantine consensus requires 2/3 honest nodes")

        results = await rag.search("SHA-256 hash")
        assert len(results) > 0
        assert "SHA-256" in results[0].content

    @pytest.mark.asyncio
    async def test_no_contradiction_detection(self, rag: BaselineRAG):
        await rag.store("P is TRUE")
        await rag.store("P is FALSE")

        assert rag.count_contradictions_detected() == 0

    @pytest.mark.asyncio
    async def test_no_byzantine_detection(self, rag: BaselineRAG):
        assert rag.count_byzantine_detected() == 0

    @pytest.mark.asyncio
    async def test_duplication_ratio(self, rag: BaselineRAG):
        for _ in range(10):
            await rag.store("same content")

        assert rag.duplication_ratio == pytest.approx(0.9)  # 9/10 are dupes
