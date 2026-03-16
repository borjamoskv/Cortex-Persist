"""Tests for ALMA Taste Engine — Sovereign Quality Discriminator."""

from __future__ import annotations

import pytest

from cortex.alma.taste import (
    GRADE_DEAD,
    GRADE_FUNCTIONAL,
    GRADE_GOAT,
    GRADE_MEDIOCRE,
    GRADE_STRONG,
    TasteEngine,
    TasteVerdict,
)


@pytest.fixture
def engine() -> TasteEngine:
    """Default TasteEngine instance."""
    return TasteEngine()


# --- Basic instantiation ---


class TestTasteEngineInit:
    def test_default_weights(self, engine: TasteEngine) -> None:
        assert engine._total_weight > 0
        assert "taste" in engine._weights
        assert "utility" in engine._weights
        # taste and utility should have 2x weight
        assert engine._weights["taste"] == 2.0
        assert engine._weights["utility"] == 2.0

    def test_custom_weights(self) -> None:
        custom = {"precision": 1.0, "utility": 1.0, "taste": 1.0}
        eng = TasteEngine(weights=custom)
        assert eng._total_weight == 3.0


# --- Empty content ---


class TestEmptyContent:
    def test_empty_string(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("")
        assert verdict.grade == GRADE_DEAD
        assert verdict.composite_score == 0.0

    def test_whitespace_only(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("   \n\t  ")
        assert verdict.grade == GRADE_DEAD
        assert verdict.composite_score == 0.0

    def test_none_like(self, engine: TasteEngine) -> None:
        """Empty content should not crash."""
        verdict = engine.evaluate("")
        assert isinstance(verdict, TasteVerdict)
        assert len(verdict.dimensions) > 0


# --- Grade classification ---


class TestGradeClassification:
    def test_grade_thresholds(self, engine: TasteEngine) -> None:
        assert engine._classify_grade(0.90) == GRADE_GOAT
        assert engine._classify_grade(0.85) == GRADE_GOAT
        assert engine._classify_grade(0.75) == GRADE_STRONG
        assert engine._classify_grade(0.70) == GRADE_STRONG
        assert engine._classify_grade(0.55) == GRADE_FUNCTIONAL
        assert engine._classify_grade(0.50) == GRADE_FUNCTIONAL
        assert engine._classify_grade(0.35) == GRADE_MEDIOCRE
        assert engine._classify_grade(0.30) == GRADE_MEDIOCRE
        assert engine._classify_grade(0.20) == GRADE_DEAD
        assert engine._classify_grade(0.0) == GRADE_DEAD


# --- Individual dimension scoring ---


class TestPrecisionDimension:
    def test_assertive_content_scores_higher(self, engine: TasteEngine) -> None:
        assertive = "The answer is 42. Latency is 15ms. Memory usage: 200MB."
        hedgy = "Maybe it could be 42. Perhaps the latency might be 15ms."
        v_assert = engine.evaluate(assertive)
        v_hedge = engine.evaluate(hedgy)
        p_assert = next(d for d in v_assert.dimensions if d.name == "precision")
        p_hedge = next(d for d in v_hedge.dimensions if d.name == "precision")
        assert p_assert.score > p_hedge.score

    def test_data_rich_boosts_precision(self, engine: TasteEngine) -> None:
        data_rich = "Response time: 15ms. Throughput: 1000x. Memory: 512MB. CPU: 95%."
        verdict = engine.evaluate(data_rich)
        precision = next(d for d in verdict.dimensions if d.name == "precision")
        assert precision.score >= 0.7


class TestUtilityDimension:
    def test_code_blocks_boost_utility(self, engine: TasteEngine) -> None:
        code = "```python\ndef hello():\n    pass\n```\nRun: `python main.py`"
        verdict = engine.evaluate(code)
        utility = next(d for d in verdict.dimensions if d.name == "utility")
        assert utility.score > 0.5

    def test_verbose_theory_penalized(self, engine: TasteEngine) -> None:
        theory = " ".join(["theoretical concept"] * 300)
        verdict = engine.evaluate(theory)
        utility = next(d for d in verdict.dimensions if d.name == "utility")
        assert utility.score < 0.3


class TestNoveltyDimension:
    def test_buzzwords_reduce_novelty(self, engine: TasteEngine) -> None:
        buzzwords = (
            "Using best practices and cutting-edge paradigm shift "
            "with seamless holistic synergy for a robust solution."
        )
        verdict = engine.evaluate(buzzwords)
        novelty = next(d for d in verdict.dimensions if d.name == "novelty")
        assert novelty.score < 0.5

    def test_unique_content_boosts_novelty(self, engine: TasteEngine) -> None:
        unique = (
            "Thermodynamic crystallization of epistemic gradients "
            "through sovereign ledger verification enables "
            "compound yield amplification across causal DAG chains."
        )
        verdict = engine.evaluate(unique)
        novelty = next(d for d in verdict.dimensions if d.name == "novelty")
        assert novelty.score >= 0.5


class TestDepthDimension:
    def test_tradeoffs_boost_depth(self, engine: TasteEngine) -> None:
        deep = (
            "The trade-off between latency and throughput is real. "
            "Because of the O(n log n) complexity, failure modes "
            "include edge cases where the constraint is violated. "
            "The bottleneck is the serialization layer."
        )
        verdict = engine.evaluate(deep)
        depth = next(d for d in verdict.dimensions if d.name == "depth")
        assert depth.score >= 0.6

    def test_shallow_content_low_depth(self, engine: TasteEngine) -> None:
        shallow = "This is a great product. It works well. Try it now."
        verdict = engine.evaluate(shallow)
        depth = next(d for d in verdict.dimensions if d.name == "depth")
        assert depth.score < 0.5


class TestRobustnessDimension:
    def test_defensive_coding_boosts_robustness(self, engine: TasteEngine) -> None:
        robust = (
            "```python\ntry:\n    validate(input)\nexcept ValueError:\n"
            "    raise\nif result is None:\n    fallback()\n```"
        )
        verdict = engine.evaluate(robust)
        robustness = next(d for d in verdict.dimensions if d.name == "robustness")
        assert robustness.score >= 0.6


class TestReusabilityDimension:
    def test_abstractions_boost_reuse(self, engine: TasteEngine) -> None:
        reusable = (
            "```python\nclass TasteEngine:\n    def evaluate(self, config: Config):\n"
            "        pass\n```\nThis API module provides a generic template."
        )
        verdict = engine.evaluate(reusable)
        reuse = next(d for d in verdict.dimensions if d.name == "reusability")
        assert reuse.score >= 0.5


class TestTasteDimension:
    def test_filler_penalized(self, engine: TasteEngine) -> None:
        filler = (
            "In summary, it is worth noting that essentially "
            "the best practices suggest a cutting-edge paradigm shift. "
            "In conclusion, fundamentally this is seamless synergy."
        )
        verdict = engine.evaluate(filler)
        taste = next(d for d in verdict.dimensions if d.name == "taste")
        assert taste.score < 0.4

    def test_zero_filler_rewarded(self, engine: TasteEngine) -> None:
        clean = (
            "We choose the Byzantine consensus model. "
            "The correct approach requires hash chain verification "
            "with O(1) lookups for each tenant partition."
        )
        verdict = engine.evaluate(clean)
        taste = next(d for d in verdict.dimensions if d.name == "taste")
        assert taste.score >= 0.5


# --- Composite scoring ---


class TestCompositeScoring:
    def test_composite_within_bounds(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("Some content to evaluate for scoring purposes.")
        assert 0.0 <= verdict.composite_score <= 1.0

    def test_high_quality_content(self, engine: TasteEngine) -> None:
        high = (
            "## Architecture Decision\n\n"
            "We choose the trade-off of higher latency (15ms) "
            "for better throughput (1000x). Because of the O(1) "
            "lookup constraint, the bottleneck shifts to the "
            "serialization layer.\n\n"
            "### Failure Modes\n- Edge case: null partition key\n"
            "- Risk: cascading timeout\n- Caveat: cold start penalty\n\n"
            "```python\ntry:\n    result = validate(config)\n"
            "except ValueError as e:\n    raise RuntimeError(e)\n```\n\n"
            "Step 1: Deploy to staging\n"
            "Step 2: Run https://example.com/healthcheck\n"
        )
        verdict = engine.evaluate(high)
        # Should be at least STRONG
        assert verdict.grade in (GRADE_GOAT, GRADE_STRONG)

    def test_low_quality_content(self, engine: TasteEngine) -> None:
        low = (
            "In summary, it is worth noting that essentially "
            "the best practices suggest leveraging synergy."
        )
        verdict = engine.evaluate(low)
        assert verdict.grade in (GRADE_MEDIOCRE, GRADE_DEAD, GRADE_FUNCTIONAL)


# --- is_mediocre ---


class TestIsMediocre:
    def test_mediocre_detected(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("")
        assert engine.is_mediocre(verdict) is True

    def test_strong_not_mediocre(self, engine: TasteEngine) -> None:
        high = (
            "## Decision\nWe choose Byzantine consensus. "
            "Because of the O(1) constraint and the trade-off "
            "between latency (15ms) and throughput (1000x), "
            "the failure mode analysis shows edge cases "
            "in the bottleneck layer.\n\n"
            "```python\ntry:\n    validate(config)\n"
            "except ValueError:\n    fallback()\n```\n\n"
            "Step 1: Run deploy\nStep 2: Check https://api.test\n"
        )
        verdict = engine.evaluate(high)
        if verdict.grade in (GRADE_GOAT, GRADE_STRONG):
            assert engine.is_mediocre(verdict) is False


# --- rank_ideas ---


class TestRankIdeas:
    def test_ranking_order(self, engine: TasteEngine) -> None:
        ideas = [
            "In summary, basically this is a paradigm shift.",
            (
                "We choose O(1) lookups. Because of the trade-off "
                "between latency (15ms) and edge case validation, "
                "```python\ndef factory(): pass\n```"
            ),
            "",
        ]
        ranked = engine.rank_ideas(ideas)
        assert len(ranked) == 3
        # Best should be first, empty last
        assert ranked[0].composite_score >= ranked[1].composite_score
        assert ranked[1].composite_score >= ranked[2].composite_score
        assert ranked[-1].grade == GRADE_DEAD

    def test_empty_list(self, engine: TasteEngine) -> None:
        assert engine.rank_ideas([]) == []


# --- to_dict serialization ---


class TestSerialization:
    def test_verdict_to_dict(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("Some content here.")
        d = verdict.to_dict()
        assert "composite_score" in d
        assert "grade" in d
        assert "verdict" in d
        assert "dimensions" in d
        assert "timestamp" in d
        assert isinstance(d["dimensions"], dict)

    def test_dimension_names_in_dict(self, engine: TasteEngine) -> None:
        verdict = engine.evaluate("Test content.")
        d = verdict.to_dict()
        expected = {"precision", "utility", "novelty", "depth", "robustness", "reusability", "taste"}
        assert set(d["dimensions"].keys()) == expected


# --- Context-aware evaluation ---


class TestContextAware:
    def test_existing_facts_boost_precision(self, engine: TasteEngine) -> None:
        ctx = {"existing_facts": ["fact1", "fact2", "fact3"]}
        verdict = engine.evaluate("Analyze the system.", ctx)
        precision = next(d for d in verdict.dimensions if d.name == "precision")
        assert "context-aware" in precision.signal

    def test_user_preferences_boost_taste(self, engine: TasteEngine) -> None:
        ctx = {"user_preferences": {"style": "industrial", "tone": "noir"}}
        content = "The industrial noir aesthetic dominates the interface."
        verdict = engine.evaluate(content, ctx)
        taste = next(d for d in verdict.dimensions if d.name == "taste")
        assert "preference-aligned" in taste.signal

    def test_novel_vs_existing(self, engine: TasteEngine) -> None:
        ctx = {"existing_facts": ["the sky is blue", "water is wet"]}
        novel = "Quantum entanglement enables sovereign cryptographic verification."
        verdict = engine.evaluate(novel, ctx)
        novelty = next(d for d in verdict.dimensions if d.name == "novelty")
        assert novelty.score >= 0.5
