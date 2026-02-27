"""Tests for the 10 Advanced Memory Strategies (Phase 4)."""

import time

from cortex.memory.bloom import BloomFilter
from cortex.memory.causal import CausalGraph, CausalLink
from cortex.memory.compression import SemanticCompressor
from cortex.memory.crdt import CRDTEngram, GCounter, LWWRegister, ORSet
from cortex.memory.episodic import TemporalAbstractor
from cortex.memory.predictive import AnticipatoryCache, CoAccessGraph
from cortex.memory.reconsolidation import ReconsolidationTracker
from cortex.memory.valence import EmotionalTag, classify_valence


class DummyEngram:
    def __init__(self, eid, content, fact_type="", embedding=None):
        self.id = eid
        self.engram_id = eid
        self.content = content
        self.fact_type = fact_type
        self.metadata = {"fact_type": fact_type, "file": "test.py"}
        self.energy_level = 0.5
        self.embedding = embedding or []


class TestPrimitives:
    def test_bloom_filter(self):
        bf = BloomFilter(expected_items=1000, fp_rate=0.01)
        bf.add("test_fact_1")
        assert bf.might_contain("test_fact_1") is True
        assert bf.might_contain("test_fact_2") is False

    def test_valence_tagging(self):
        v1 = classify_valence("This bug caused a huge error.")
        assert v1.tag == EmotionalTag.NEGATIVE
        assert v1.valence < 0
        assert v1.energy_multiplier > 1.0

        v2 = classify_valence("Implemented the ART Gate", fact_type="decision")
        assert v2.tag == EmotionalTag.POSITIVE
        assert v2.valence > 0
        assert v2.energy_multiplier > 1.0

        v3 = classify_valence("Standard info")
        assert v3.tag == EmotionalTag.NEUTRAL
        assert v3.valence == 0.0

    def test_reconsolidation_tracker(self):
        tracker = ReconsolidationTracker(window_seconds=0.1)
        tracker.on_access("e1")
        tracker.on_access("e2")
        tracker.on_access("e3")

        assert tracker.labile_count == 3
        
        # Confirm e1 -> boost
        boost = tracker.confirm("e1")
        assert boost > 0

        # Contradict e2 -> neutral energy for update
        delta = tracker.contradict("e2")
        assert delta == 0.0

        # Expire e3
        time.sleep(0.15)
        expired = tracker.sweep()
        assert len(expired) == 1
        assert expired[0][0] == "e3"
        assert expired[0][1] < 0  # Penalty


class TestComposites:
    def test_semantic_compressor(self):
        comp = SemanticCompressor(min_cluster_size=2)
        engrams = [
            DummyEngram("1", "Function setup_db uses sqlite."),
            DummyEngram("2", "Function setup_db uses sqlite."),
            DummyEngram("3", "The setup_db is using sqlite."),
        ]
        res = comp.compress(engrams)
        assert res.original_count == 3
        # Should deduplicate exact/close matches
        assert res.compressed_tokens <= res.original_tokens
        assert res.compression_ratio <= 1.0

    def test_temporal_abstractor(self):
        abst = TemporalAbstractor()
        engrams = [
            DummyEngram("1", "Decided to use CRDTs", fact_type="decision"),
            DummyEngram("2", "Fixed race condition error", fact_type="error"),
            DummyEngram("3", "Learned that bloom is O(1)", fact_type="bridge"),
        ]
        ep = abst.abstract(engrams, "2025-02-26", "cortex")
        assert ep.period_label == "2025-02-26"
        assert ep.engram_count == 3
        assert len(ep.key_decisions) == 1
        assert len(ep.errors_resolved) == 1
        assert len(ep.key_learnings) == 1
        assert ep.density > 0

    def test_causal_graph(self):
        graph = CausalGraph()
        graph.add_link(CausalLink("cause1", "effect1"))
        graph.add_link(CausalLink("effect1", "effect2"))

        assert "effect1" in [link.effect_id for link in graph.effects_of("cause1")]
        assert "cause1" in graph.root_causes("effect2")
        
        chain = graph.impact_chain("cause1")
        assert "effect1" in chain
        assert "effect2" in chain

        # Zombie detection: "effect2" requires "cause1". If "cause1" is dead:
        zombies = graph.find_zombies(alive_ids={"effect2", "effect1"})
        # cause1 is missing from alive_ids, so effect1 is a zombie, which makes effect2 a zombie.
        # Actually, effect1's root cause is missing.
        assert "effect1" in zombies
        assert "effect2" in zombies


class TestDistributed:
    def test_crdt_gcounter(self):
        c1 = GCounter()
        c1.increment("agent_A", 2)
        
        c2 = GCounter()
        c2.increment("agent_B", 3)
        c2.increment("agent_A", 1)  # Stale

        merged = c1.merge(c2)
        assert merged.value == 5  # max(2,1) + max(0,3)

    def test_crdt_lww_register(self):
        r1 = LWWRegister("old", timestamp=100, agent_id="A")
        r2 = LWWRegister("new", timestamp=200, agent_id="B")
        merged = r1.merge(r2)
        assert merged.value == "new"
        assert merged.agent_id == "B"

    def test_crdt_orset(self):
        s1 = ORSet({"tag1": 100})
        s2 = ORSet({"tag2": 200, "tag1": 50})
        merged = s1.merge(s2)
        assert "tag1" in merged.elements
        assert "tag2" in merged.elements

    def test_crdt_engram_merge(self):
        e1 = CRDTEngram(engram_id="e1")
        e1.access_count.increment("A", 5)
        e1.tags.add("ui")

        e2 = CRDTEngram(engram_id="e1")
        e2.access_count.increment("B", 3)
        e2.tags.add("backend")

        merged = e1.merge(e2)
        assert merged.access_count.value == 8
        assert "ui" in merged.tags.elements
        assert "backend" in merged.tags.elements


class TestMeta:
    def test_co_access_graph(self):
        graph = CoAccessGraph(decay_factor=0.5)
        graph.record_access("A")
        graph.record_access("B")
        graph.record_access("C")
        graph.record_access("A")
        graph.record_access("B")

        preds = graph.predict_next("A", top_k=1)
        assert preds[0][0] == "B"  # A is followed by B

        graph.decay_all()
        # Edges decayed but still exist
        assert graph.edge_count > 0

    def test_anticipatory_cache(self):
        cache = AnticipatoryCache(prefetch_threshold=0.1)
        # Train sequence A -> B
        cache.on_access("A", DummyEngram("A", "content"))
        cache.on_access("B", DummyEngram("B", "content"))

        # Access A again, should predict B
        res = cache.on_access("A")
        assert "B" in res.prefetched_ids
        assert cache.hit_rate > 0
