"""CORTEX v7+ — Metamemory Tests.

Tests for MetamemoryMonitor: FOK, JOL, calibration, introspection,
and knowledge gap (TOT) detection.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cortex.memory.metamemory import (
    _MIN_CALIBRATION_SAMPLES,
    _TOT_FAILURE_THRESHOLD,
    _TOT_FOK_FLOOR,
    MemoryCard,
    MetacognitiveJudge,
    MetaJudgment,
    MetamemoryIndex,
    MetamemoryMonitor,
    RetrievalOutcome,
    Verdict,
    build_memory_card,
    detect_repair_needed,
)

# ─── Helpers ──────────────────────────────────────────────────────────


class _FakeEngram:
    """Minimal engram stub for testing — avoids importing heavy models."""

    def __init__(
        self,
        embedding: list[float] | None = None,
        content: str = "test fact",
        metadata: dict | None = None,
        entangled_refs: list[str] | None = None,
        energy_level: float = 1.0,
    ):
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.content = content
        self.metadata = metadata or {}
        self.entangled_refs = entangled_refs or []
        self.energy_level = energy_level

    def compute_decay(self) -> float:
        return self.energy_level


def _unit_vec(dim: int = 3, axis: int = 0) -> list[float]:
    """Create a unit vector along a given axis."""
    v = [0.0] * dim
    v[axis] = 1.0
    return v


def _similar_vec(base: list[float], noise: float = 0.1) -> list[float]:
    """Create a vector similar to base with slight perturbation."""
    return [x + noise * (i % 2 * 2 - 1) for i, x in enumerate(base)]


# ─── MetaJudgment Model Tests ────────────────────────────────────────


class TestMetaJudgment:
    def test_default_values(self):
        """Default MetaJudgment has zero scores and is not TOT."""
        j = MetaJudgment()
        assert j.fok_score == 0.0
        assert j.jol_score == 0.0
        assert j.confidence == 0.0
        assert j.accessibility == 0.0
        assert j.tip_of_tongue is False
        assert j.source == "introspect"

    def test_frozen_immutability(self):
        """MetaJudgment is frozen — cannot mutate fields."""
        j = MetaJudgment(fok_score=0.9)
        with pytest.raises(AttributeError):
            j.fok_score = 0.5  # type: ignore[misc]

    def test_custom_values(self):
        """MetaJudgment accepts custom field values."""
        j = MetaJudgment(
            fok_score=0.8,
            jol_score=0.7,
            confidence=0.6,
            accessibility=0.5,
            tip_of_tongue=True,
            source="fok",
        )
        assert j.fok_score == 0.8
        assert j.jol_score == 0.7
        assert j.confidence == 0.6
        assert j.accessibility == 0.5
        assert j.tip_of_tongue is True
        assert j.source == "fok"


class TestRetrievalOutcome:
    def test_default_values(self):
        """RetrievalOutcome has sensible defaults."""
        o = RetrievalOutcome()
        assert o.query == ""
        assert o.predicted_confidence == 0.0
        assert o.actual_success is False
        assert o.retrieval_score == 0.0
        assert o.timestamp > 0

    def test_frozen(self):
        """RetrievalOutcome is frozen."""
        o = RetrievalOutcome(query="test")
        with pytest.raises(AttributeError):
            o.query = "mutated"  # type: ignore[misc]


# ─── FOK Tests ────────────────────────────────────────────────────────


class TestFOK:
    def test_no_candidates_returns_zero(self):
        """Empty candidates → FOK = 0."""
        monitor = MetamemoryMonitor()
        j = monitor.judge_fok([0.1, 0.2, 0.3], [])
        assert j.fok_score == 0.0
        assert j.accessibility == 0.0

    def test_no_query_embedding_returns_zero(self):
        """Empty query embedding → FOK = 0."""
        monitor = MetamemoryMonitor()
        e = _FakeEngram(embedding=[0.1, 0.2, 0.3])
        j = monitor.judge_fok([], [e])
        assert j.fok_score == 0.0

    def test_identical_embedding_high_fok(self):
        """Identical embeddings → high FOK."""
        monitor = MetamemoryMonitor()
        emb = [0.5, 0.5, 0.5]
        e = _FakeEngram(embedding=emb)
        j = monitor.judge_fok(emb, [e])
        assert j.fok_score > 0.8
        assert j.accessibility > 0.5

    def test_orthogonal_embedding_low_fok(self):
        """Orthogonal embeddings → low FOK."""
        monitor = MetamemoryMonitor()
        query = _unit_vec(3, 0)  # [1, 0, 0]
        engram = _FakeEngram(embedding=_unit_vec(3, 2))  # [0, 0, 1]
        j = monitor.judge_fok(query, [engram])
        assert j.fok_score < 0.3

    def test_partial_match_moderate_fok(self):
        """Partial matches → moderate FOK (knowledge exists but not exact)."""
        monitor = MetamemoryMonitor(fok_threshold=0.95)  # Strict threshold
        query = [1.0, 0.0, 0.0]
        engram = _FakeEngram(embedding=[0.5, 0.8, 0.2])  # cosine ~0.52
        j = monitor.judge_fok(query, [engram])
        assert 0.2 < j.fok_score < 0.95

    def test_tot_detection(self):
        """High FOK + below-threshold similarity → Tip-of-Tongue."""
        monitor = MetamemoryMonitor(fok_threshold=0.99)  # Very strict
        query = [0.5, 0.5, 0.5]
        # Similar but not identical — many partial matches
        engrams = [
            _FakeEngram(embedding=_similar_vec(query, 0.05)),
            _FakeEngram(embedding=_similar_vec(query, 0.08)),
            _FakeEngram(embedding=_similar_vec(query, 0.1)),
        ]
        j = monitor.judge_fok(query, engrams)
        # FOK should be high (lots of partial matches), but threshold very strict
        assert j.source == "fok"

    def test_decayed_engram_lower_accessibility(self):
        """Low-energy engrams have lower accessibility."""
        monitor = MetamemoryMonitor()
        emb = [0.5, 0.5, 0.5]
        fresh = _FakeEngram(embedding=emb, energy_level=1.0)
        decayed = _FakeEngram(embedding=emb, energy_level=0.1)

        j_fresh = monitor.judge_fok(emb, [fresh])
        j_decayed = monitor.judge_fok(emb, [decayed])

        assert j_fresh.accessibility > j_decayed.accessibility


# ─── JOL Tests ────────────────────────────────────────────────────────


class TestJOL:
    def test_rich_engram_high_jol(self):
        """Well-encoded engram → high JOL."""
        monitor = MetamemoryMonitor()
        engram = _FakeEngram(
            embedding=[0.5] * 384,  # Full-size embedding
            content="A detailed decision about using Pydantic v2 for all models in CORTEX",
            metadata={
                "type": "decision",
                "project": "cortex",
                "session": "abc",
                "confidence": "C5",
                "tool": "gemini",
            },
            entangled_refs=["ref-1", "ref-2", "ref-3"],
        )
        jol = monitor.judge_jol(engram)
        assert jol > 0.6

    def test_sparse_engram_low_jol(self):
        """Minimally encoded engram → low JOL."""
        monitor = MetamemoryMonitor()
        engram = _FakeEngram(
            embedding=[0.001, 0.001, 0.001],  # Tiny embedding
            content="x",  # Almost no content
            metadata={},
            entangled_refs=[],
        )
        jol = monitor.judge_jol(engram)
        assert jol < 0.3

    def test_no_embedding_very_low_jol(self):
        """Engram with no embedding → very low JOL."""
        monitor = MetamemoryMonitor()
        engram = _FakeEngram(embedding=[])
        jol = monitor.judge_jol(engram)
        assert jol < 0.3

    def test_jol_bounded(self):
        """JOL is always in [0.0, 1.0]."""
        monitor = MetamemoryMonitor()
        # Even a maximally rich engram
        engram = _FakeEngram(
            embedding=[1.0] * 1000,
            content="x" * 500,
            metadata={f"k{i}": i for i in range(20)},
            entangled_refs=[f"ref-{i}" for i in range(10)],
        )
        jol = monitor.judge_jol(engram)
        assert 0.0 <= jol <= 1.0


# ─── Calibration Tests ───────────────────────────────────────────────


class TestCalibration:
    def test_insufficient_data(self):
        """Returns -1.0 when not enough outcomes recorded."""
        monitor = MetamemoryMonitor()
        assert monitor.calibration_score() == -1.0

    def test_perfect_calibration(self):
        """Perfect predictions → Brier score ≈ 0."""
        monitor = MetamemoryMonitor()
        for _ in range(_MIN_CALIBRATION_SAMPLES):
            monitor.record_outcome(
                RetrievalOutcome(
                    query="test",
                    predicted_confidence=1.0,
                    actual_success=True,
                    retrieval_score=0.95,
                )
            )
        brier = monitor.calibration_score()
        assert brier == pytest.approx(0.0, abs=0.01)

    def test_terrible_calibration(self):
        """Always wrong predictions → Brier score ≈ 1.0."""
        monitor = MetamemoryMonitor()
        for _ in range(_MIN_CALIBRATION_SAMPLES):
            monitor.record_outcome(
                RetrievalOutcome(
                    query="test",
                    predicted_confidence=1.0,
                    actual_success=False,
                    retrieval_score=0.0,
                )
            )
        brier = monitor.calibration_score()
        assert brier == pytest.approx(1.0, abs=0.01)

    def test_mixed_calibration(self):
        """Mixed outcomes → Brier between 0 and 1."""
        monitor = MetamemoryMonitor()
        for i in range(_MIN_CALIBRATION_SAMPLES):
            monitor.record_outcome(
                RetrievalOutcome(
                    query=f"q{i}",
                    predicted_confidence=0.7,
                    actual_success=i % 2 == 0,  # 50% success
                    retrieval_score=0.5,
                )
            )
        brier = monitor.calibration_score()
        assert 0.0 < brier < 1.0


# ─── Introspection Tests ─────────────────────────────────────────────


class TestIntrospect:
    def test_introspect_with_good_match(self):
        """Good retrieval match → high confidence judgment."""
        monitor = MetamemoryMonitor()
        emb = [0.5, 0.5, 0.5]
        engram = _FakeEngram(
            embedding=emb,
            content="Detailed technical decision about X",
            metadata={"type": "decision", "confidence": "C5"},
        )
        j = monitor.introspect(emb, [engram], retrieval_score=0.92)
        assert j.source == "introspect"
        assert j.fok_score > 0.5
        assert j.jol_score > 0.0
        assert j.confidence > 0.3

    def test_introspect_with_no_candidates(self):
        """No candidates → low everything."""
        monitor = MetamemoryMonitor()
        j = monitor.introspect([0.5, 0.5], [], retrieval_score=0.0)
        assert j.fok_score == 0.0
        assert j.confidence < 0.1

    def test_introspect_fields_bounded(self):
        """All introspection fields are in [0, 1]."""
        monitor = MetamemoryMonitor()
        emb = [1.0] * 10
        engram = _FakeEngram(embedding=emb, content="x" * 300)
        j = monitor.introspect(emb, [engram], retrieval_score=1.0)
        assert 0.0 <= j.fok_score <= 1.0
        assert 0.0 <= j.jol_score <= 1.0
        assert 0.0 <= j.confidence <= 1.0
        assert 0.0 <= j.accessibility <= 1.0


# ─── Knowledge Gaps (TOT) Tests ──────────────────────────────────────


class TestKnowledgeGaps:
    def test_no_gaps_initially(self):
        """Fresh monitor has no knowledge gaps."""
        monitor = MetamemoryMonitor()
        assert monitor.knowledge_gaps() == []

    def test_repeated_failures_create_gap(self):
        """Repeated high-FOK failures → knowledge gap detected."""
        monitor = MetamemoryMonitor()
        for _ in range(_TOT_FAILURE_THRESHOLD + 1):
            monitor.record_outcome(
                RetrievalOutcome(
                    query="how to deploy cortex",
                    predicted_confidence=_TOT_FOK_FLOOR + 0.1,
                    actual_success=False,
                    retrieval_score=0.1,
                )
            )
        gaps = monitor.knowledge_gaps()
        assert "how to deploy cortex" in gaps

    def test_successful_retrieval_no_gap(self):
        """Successful retrievals don't create knowledge gaps."""
        monitor = MetamemoryMonitor()
        for _ in range(10):
            monitor.record_outcome(
                RetrievalOutcome(
                    query="known fact",
                    predicted_confidence=0.9,
                    actual_success=True,
                    retrieval_score=0.95,
                )
            )
        assert monitor.knowledge_gaps() == []

    def test_low_fok_failures_no_gap(self):
        """Low-FOK failures are not TOT — they're recognized absence."""
        monitor = MetamemoryMonitor()
        for _ in range(5):
            monitor.record_outcome(
                RetrievalOutcome(
                    query="unknown topic",
                    predicted_confidence=0.1,  # Low FOK
                    actual_success=False,
                    retrieval_score=0.0,
                )
            )
        assert "unknown topic" not in monitor.knowledge_gaps()


# ─── Calibration Report Tests ────────────────────────────────────────


class TestCalibrationReport:
    def test_report_structure(self):
        """Report contains all expected keys."""
        monitor = MetamemoryMonitor()
        report = monitor.calibration_report()
        expected_keys = {
            "brier_score",
            "calibration_tier",
            "segmented_brier",
            "active_domains",
            "total_outcomes",
            "successes",
            "failures",
            "success_rate",
            "avg_predicted_confidence",
            "knowledge_gaps",
            "tot_patterns",
            "tracked_queries",
        }
        assert expected_keys == set(report.keys())

    def test_empty_report_tier(self):
        """Empty monitor reports insufficient_data tier."""
        monitor = MetamemoryMonitor()
        report = monitor.calibration_report()
        assert report["calibration_tier"] == "insufficient_data"
        assert report["total_outcomes"] == 0

    def test_report_with_data(self):
        """Report with outcomes shows correct stats."""
        monitor = MetamemoryMonitor()
        for i in range(20):
            monitor.record_outcome(
                RetrievalOutcome(
                    query=f"q{i}",
                    predicted_confidence=0.8,
                    actual_success=i < 16,  # 80% success rate
                    retrieval_score=0.7 if i < 16 else 0.1,
                )
            )
        report = monitor.calibration_report()
        assert report["total_outcomes"] == 20
        assert report["successes"] == 16
        assert report["failures"] == 4
        assert report["success_rate"] == pytest.approx(0.8, abs=0.01)
        assert report["calibration_tier"] in {"excellent", "good", "fair", "poor"}


# ─── Repr Test ────────────────────────────────────────────────────────


class TestRepr:
    def test_repr_is_informative(self):
        """__repr__ contains useful state info."""
        monitor = MetamemoryMonitor()
        r = repr(monitor)
        assert "MetamemoryMonitor" in r
        assert "outcomes=0" in r
        assert "brier=n/a" in r
        assert "knowledge_gaps=0" in r


# ═══════════════════════════════════════════════════════════════════════
# SCHEMA LAYER TESTS — MemoryCard, MetamemoryIndex, MetacognitiveJudge
# ═══════════════════════════════════════════════════════════════════════


class TestMemoryCard:
    def test_required_field_memory_id(self):
        card = MemoryCard(memory_id="mem_001")
        assert card.memory_id == "mem_001"

    def test_defaults(self):
        card = MemoryCard(memory_id="mem_def")
        assert card.existence_probability == 1.0
        assert card.retrieval_confidence == 1.0
        assert card.access_frequency == 0
        assert card.semantic_coordinates == []
        assert card.consolidation_status == "unknown"
        assert card.repair_needed is False
        assert card.emotional_weight == 1.0

    def test_frozen(self):
        card = MemoryCard(memory_id="mem_frz")
        with pytest.raises(ValidationError):
            card.memory_id = "changed"  # type: ignore[misc]

    def test_user_schema_example(self):
        """Validates the exact user-provided schema example."""
        card = MemoryCard(
            memory_id="mem_9a3f",
            existence_probability=0.94,
            retrieval_confidence=0.87,
            access_frequency=127,
            semantic_coordinates=[0.23, -0.87, 0.45],
            consolidation_status="active",
            repair_needed=False,
            emotional_weight=0.65,
        )
        assert card.existence_probability == 0.94
        assert card.retrieval_confidence == 0.87
        assert card.access_frequency == 127
        assert card.consolidation_status == "active"
        assert card.emotional_weight == 0.65

    def test_bounds_existence_probability(self):
        with pytest.raises(ValueError):
            MemoryCard(memory_id="bad", existence_probability=1.5)

    def test_bounds_retrieval_confidence(self):
        with pytest.raises(ValueError):
            MemoryCard(memory_id="bad", retrieval_confidence=2.0)

    def test_bounds_emotional_weight(self):
        with pytest.raises(ValueError):
            MemoryCard(memory_id="bad", emotional_weight=3.0)

    def test_bounds_access_frequency(self):
        with pytest.raises(ValueError):
            MemoryCard(memory_id="bad", access_frequency=-1)


class TestRepairDetection:
    def test_healthy_memory(self):
        assert detect_repair_needed(energy_level=0.8, success_rate=0.9) is False

    def test_contradiction_triggers(self):
        assert detect_repair_needed(0.8, 0.9, contradiction_count=1) is True

    def test_low_energy_triggers(self):
        assert detect_repair_needed(energy_level=0.05, success_rate=0.9) is True

    def test_low_success_rate_triggers(self):
        assert detect_repair_needed(energy_level=0.8, success_rate=0.3) is True

    def test_stale_triggers(self):
        assert detect_repair_needed(0.8, 0.9, days_since_access=100.0) is True

    def test_boundary_energy(self):
        assert detect_repair_needed(energy_level=0.1, success_rate=0.9) is False

    def test_boundary_success_rate(self):
        assert detect_repair_needed(energy_level=0.8, success_rate=0.5) is False


class TestBuildMemoryCard:
    def test_defaults(self):
        card = build_memory_card("mem_factory")
        assert card.memory_id == "mem_factory"
        assert card.existence_probability == 1.0
        assert card.repair_needed is False

    def test_existence_formula(self):
        card = build_memory_card("ep", energy_level=0.5, success_rate=0.8)
        assert abs(card.existence_probability - 0.4) < 0.01

    def test_retrieval_confidence_formula(self):
        card = build_memory_card("rc", energy_level=0.6, retrieval_similarity=0.9)
        assert abs(card.retrieval_confidence - 0.54) < 0.01

    def test_repair_detected(self):
        card = build_memory_card("rp", energy_level=0.05, success_rate=0.9)
        assert card.repair_needed is True

    def test_consolidation_status(self):
        card = build_memory_card("cs", consolidation_status="matured")
        assert card.consolidation_status == "matured"

    def test_valence_clamped(self):
        card = build_memory_card("vc", valence_multiplier=2.5)
        assert card.emotional_weight == 2.0


class TestMetamemoryIndex:
    def _card(self, mid: str, conf: float = 0.8, repair: bool = False) -> MemoryCard:
        return MemoryCard(memory_id=mid, retrieval_confidence=conf, repair_needed=repair)

    def test_register_and_introspect(self):
        idx = MetamemoryIndex()
        card = self._card("m1")
        idx.register(card)
        assert idx.introspect("m1") is card
        assert idx.size == 1

    def test_introspect_missing(self):
        idx = MetamemoryIndex()
        assert idx.introspect("x") is None

    def test_register_batch(self):
        idx = MetamemoryIndex()
        cards = [self._card(f"m{i}") for i in range(5)]
        assert idx.register_batch(cards) == 5
        assert len(idx) == 5

    def test_introspect_batch(self):
        idx = MetamemoryIndex()
        idx.register_batch([self._card(f"m{i}") for i in range(3)])
        result = idx.introspect_batch(["m0", "m2", "m99"])
        assert len(result) == 2

    def test_remove(self):
        idx = MetamemoryIndex()
        idx.register(self._card("m1"))
        assert idx.remove("m1") is True
        assert idx.remove("m1") is False

    def test_query_weak_memories(self):
        idx = MetamemoryIndex()
        idx.register(self._card("strong", conf=0.9))
        idx.register(self._card("weak", conf=0.2))
        idx.register(self._card("weaker", conf=0.1))
        weak = idx.query_weak_memories(threshold=0.5)
        assert len(weak) == 2
        assert weak[0].memory_id == "weaker"

    def test_needs_repair(self):
        idx = MetamemoryIndex()
        idx.register(self._card("ok", repair=False))
        idx.register(self._card("broken", repair=True))
        assert len(idx.needs_repair()) == 1

    def test_contains(self):
        idx = MetamemoryIndex()
        idx.register(self._card("m1"))
        assert "m1" in idx
        assert "m2" not in idx

    def test_summary_stats_empty(self):
        idx = MetamemoryIndex()
        assert idx.summary_stats().total_memories == 0

    def test_summary_stats(self):
        idx = MetamemoryIndex()
        idx.register(
            MemoryCard(
                memory_id="m1",
                existence_probability=0.8,
                retrieval_confidence=0.6,
                repair_needed=True,
                consolidation_status="deceased",
            )
        )
        idx.register(
            MemoryCard(memory_id="m2", existence_probability=0.4, retrieval_confidence=0.4)
        )
        stats = idx.summary_stats()
        assert stats.total_memories == 2
        assert abs(stats.mean_existence_probability - 0.6) < 0.01
        assert stats.memories_needing_repair == 1
        assert stats.deceased_memories == 1


class TestMetacognitiveJudge:
    def _card(
        self, mid: str = "m1", conf: float = 0.8, exist: float = 0.9, repair: bool = False
    ) -> MemoryCard:
        return MemoryCard(
            memory_id=mid,
            retrieval_confidence=conf,
            existence_probability=exist,
            repair_needed=repair,
        )

    def test_respond(self):
        j = MetacognitiveJudge()
        assert j.judge([self._card(conf=0.85, exist=0.9)]) == Verdict.RESPOND

    def test_search_more(self):
        j = MetacognitiveJudge()
        assert j.judge([self._card(conf=0.5, exist=0.9)]) == Verdict.SEARCH_MORE

    def test_abstain_low_conf(self):
        j = MetacognitiveJudge()
        assert j.judge([self._card(conf=0.1)]) == Verdict.ABSTAIN

    def test_abstain_empty(self):
        j = MetacognitiveJudge()
        assert j.judge([]) == Verdict.ABSTAIN

    def test_abstain_all_repair(self):
        j = MetacognitiveJudge()
        cards = [self._card(conf=0.9, repair=True), self._card(mid="m2", conf=0.8, repair=True)]
        assert j.judge(cards) == Verdict.ABSTAIN

    def test_ignores_repair_flagged(self):
        j = MetacognitiveJudge()
        cards = [
            self._card(mid="bad", conf=0.95, repair=True),
            self._card(mid="good", conf=0.75, exist=0.8),
        ]
        assert j.judge(cards) == Verdict.RESPOND

    def test_low_existence_forces_search(self):
        j = MetacognitiveJudge()
        assert j.judge([self._card(conf=0.8, exist=0.3)]) == Verdict.SEARCH_MORE

    def test_custom_thresholds(self):
        j = MetacognitiveJudge(respond_confidence=0.9, search_confidence=0.5)
        assert j.judge([self._card(conf=0.85, exist=0.9)]) == Verdict.SEARCH_MORE

    def test_judge_with_rationale(self):
        j = MetacognitiveJudge()
        verdict, rationale = j.judge_with_rationale([self._card(conf=0.85, exist=0.9)])
        assert verdict == Verdict.RESPOND
        assert rationale["verdict"] == "respond"
        assert rationale["best_memory_id"] == "m1"
        assert "respond_confidence" in rationale["thresholds"]

    def test_verdict_values(self):
        assert Verdict.RESPOND == "respond"
        assert Verdict.SEARCH_MORE == "search_more"
        assert Verdict.ABSTAIN == "abstain"
