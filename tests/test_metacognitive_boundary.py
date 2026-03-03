"""CORTEX v8.0 — MetacognitiveBoundary Test Suite.

Sprint 1: Tests for the LLM↔Memory bridge.

Covers:
  - EpistemicSignal derivation from MetaJudgment + Verdict
  - MetacognitiveContext construction and hard-block logic
  - build_epistemic_preamble() content and capping
  - inject_epistemic_preamble() placement and format
  - append_retrieval_plan_request() suffix injection
  - verify_retrieval_plan_declared() parsing
  - extract_declared_confidence() extraction
  - check_confidence_consistency() gap detection
"""

from __future__ import annotations

import pytest

from cortex.llm.metacognitive_boundary import (
    EpistemicSignal,
    append_retrieval_plan_request,
    build_epistemic_preamble,
    build_metacognitive_context,
    check_confidence_consistency,
    extract_declared_confidence,
    inject_epistemic_preamble,
    verify_retrieval_plan_declared,
)
from cortex.memory.metamemory import (
    MemoryCard,
    MetaJudgment,
    Verdict,
    build_memory_card,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _judgment(
    fok: float = 0.8,
    jol: float = 0.7,
    confidence: float = 0.75,
    accessibility: float = 0.8,
    tot: bool = False,
) -> MetaJudgment:
    return MetaJudgment(
        fok_score=fok,
        jol_score=jol,
        confidence=confidence,
        accessibility=accessibility,
        tip_of_tongue=tot,
    )


def _card(
    memory_id: str = "mem-001",
    retrieval_confidence: float = 0.9,
    existence_probability: float = 0.95,
    repair_needed: bool = False,
    consolidation_status: str = "matured",
) -> MemoryCard:
    return build_memory_card(
        memory_id,
        energy_level=retrieval_confidence,
        success_rate=existence_probability,
        retrieval_similarity=retrieval_confidence,
    )


# ═══════════════════════════════════════════════════════════════════════
# EpistemicSignal derivation
# ═══════════════════════════════════════════════════════════════════════


class TestEpistemicSignalDerivation:
    def test_tot_overrides_respond_verdict(self):
        """Tip-of-tongue takes priority — even if verdict is RESPOND."""
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(tot=True),
        )
        assert ctx.signal == EpistemicSignal.TOT

    def test_respond_verdict_high_confidence_is_confident(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(confidence=0.85, tot=False),
        )
        assert ctx.signal == EpistemicSignal.CONFIDENT

    def test_respond_verdict_low_confidence_is_uncertain(self):
        """RESPOND with low confidence → UNCERTAIN (not CONFIDENT)."""
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(confidence=0.1, tot=False),
        )
        # confidence < _RESPOND_CONFIDENCE_FLOOR → UNCERTAIN
        assert ctx.signal == EpistemicSignal.UNCERTAIN

    def test_search_more_verdict_is_partial(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.SEARCH_MORE,
            judgment=_judgment(confidence=0.4, tot=False),
        )
        assert ctx.signal == EpistemicSignal.PARTIAL

    def test_abstain_verdict_is_uncertain(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN,
            judgment=_judgment(confidence=0.1, tot=False),
        )
        assert ctx.signal == EpistemicSignal.UNCERTAIN


# ═══════════════════════════════════════════════════════════════════════
# MetacognitiveContext
# ═══════════════════════════════════════════════════════════════════════


class TestMetacognitiveContext:
    def test_should_hard_block_low_confidence_abstain(self):
        """Very low confidence + ABSTAIN → hard block."""
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN,
            judgment=_judgment(confidence=0.05),  # Below _ABSTAIN_CONFIDENCE_CAP
        )
        assert ctx.should_hard_block is True

    def test_should_not_hard_block_respond(self):
        """RESPOND verdict never triggers hard block."""
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(confidence=0.9),
        )
        assert ctx.should_hard_block is False

    def test_should_not_hard_block_moderate_abstain(self):
        """ABSTAIN with moderate confidence does not hard block."""
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN,
            judgment=_judgment(confidence=0.4),  # Above _ABSTAIN_CONFIDENCE_CAP
        )
        assert ctx.should_hard_block is False

    def test_card_summaries_empty_when_no_cards(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
        )
        assert ctx.card_summaries == []

    def test_card_summaries_structure(self):
        """card_summaries returns expected dict keys."""
        card = _card()
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
            memory_cards=[card],
        )
        summaries = ctx.card_summaries
        assert len(summaries) == 1
        s = summaries[0]
        assert "id" in s
        assert "confidence" in s
        assert "existence" in s
        assert "status" in s
        assert "needs_repair" in s
        assert "emotional_weight" in s

    def test_knowledge_gaps_default_empty(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
        )
        assert ctx.knowledge_gaps == []

    def test_knowledge_gaps_populated(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
            knowledge_gaps=["cortex reconsolidation", "semantic navigation"],
        )
        assert len(ctx.knowledge_gaps) == 2


# ═══════════════════════════════════════════════════════════════════════
# build_epistemic_preamble()
# ═══════════════════════════════════════════════════════════════════════


class TestBuildEpistemicPreamble:
    def test_preamble_contains_cortex_header(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        preamble = build_epistemic_preamble(ctx)
        assert "[CORTEX EPISTEMIC STATE]" in preamble

    def test_preamble_contains_verdict(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        preamble = build_epistemic_preamble(ctx)
        assert "RESPOND" in preamble

    def test_preamble_contains_fok_jol(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment(fok=0.75, jol=0.65)
        )
        preamble = build_epistemic_preamble(ctx)
        assert "FOK" in preamble
        assert "JOL" in preamble

    def test_preamble_contains_tot_warning_when_active(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment(tot=True)
        )
        preamble = build_epistemic_preamble(ctx)
        assert "TIP-OF-TONGUE" in preamble

    def test_preamble_contains_hard_block_when_triggered(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN, judgment=_judgment(confidence=0.05)
        )
        preamble = build_epistemic_preamble(ctx)
        assert "HARD BLOCK" in preamble

    def test_preamble_contains_knowledge_gaps(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
            knowledge_gaps=["test gap"],
        )
        preamble = build_epistemic_preamble(ctx)
        assert "test gap" in preamble

    def test_preamble_contains_memory_count(self):
        cards = [_card("m1"), _card("m2")]
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND,
            judgment=_judgment(),
            memory_cards=cards,
        )
        preamble = build_epistemic_preamble(ctx)
        assert "2 engrams" in preamble

    def test_preamble_respects_max_length(self):
        """Preamble is capped at _MAX_PREAMBLE_CHARS."""
        from cortex.llm.metacognitive_boundary import _MAX_PREAMBLE_CHARS

        # Create a context with many gaps to bloat the preamble
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN,
            judgment=_judgment(tot=True, confidence=0.01),
            knowledge_gaps=[f"gap-{i}" for i in range(100)],
            memory_cards=[_card(f"m{i}") for i in range(50)],
        )
        preamble = build_epistemic_preamble(ctx)
        assert len(preamble) <= _MAX_PREAMBLE_CHARS

    def test_preamble_contains_respond_instruction(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        preamble = build_epistemic_preamble(ctx)
        assert "RESPOND" in preamble
        assert "calibrated confidence" in preamble.lower()

    def test_preamble_contains_abstain_instruction(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.ABSTAIN, judgment=_judgment(confidence=0.4)
        )
        preamble = build_epistemic_preamble(ctx)
        assert "don't know" in preamble.lower() or "insufficient" in preamble.lower()


# ═══════════════════════════════════════════════════════════════════════
# inject_epistemic_preamble()
# ═══════════════════════════════════════════════════════════════════════


class TestInjectEpistemicPreamble:
    def test_preamble_placed_before_system_prompt(self):
        """The epistemic preamble should appear BEFORE the main system prompt."""
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        system = "You are a helpful assistant."
        result = inject_epistemic_preamble(system, ctx)

        preamble_pos = result.index("[CORTEX EPISTEMIC STATE]")
        system_pos = result.index("You are a helpful assistant.")
        assert preamble_pos < system_pos

    def test_empty_system_prompt_returns_preamble_only(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        result = inject_epistemic_preamble("", ctx)
        assert "[CORTEX EPISTEMIC STATE]" in result

    def test_original_system_prompt_preserved(self):
        ctx = build_metacognitive_context(
            verdict=Verdict.RESPOND, judgment=_judgment()
        )
        system = "You are the Sovereign Architect."
        result = inject_epistemic_preamble(system, ctx)
        assert "You are the Sovereign Architect." in result


# ═══════════════════════════════════════════════════════════════════════
# append_retrieval_plan_request()
# ═══════════════════════════════════════════════════════════════════════


class TestAppendRetrievalPlanRequest:
    def test_suffix_appended(self):
        result = append_retrieval_plan_request("What is reconsolidation?")
        assert "<retrieval_plan>" in result
        assert "</retrieval_plan>" in result

    def test_original_message_preserved(self):
        msg = "Explain the Brier score."
        result = append_retrieval_plan_request(msg)
        assert msg in result

    def test_suffix_after_message(self):
        msg = "Hello"
        result = append_retrieval_plan_request(msg)
        assert result.startswith(msg)


# ═══════════════════════════════════════════════════════════════════════
# verify_retrieval_plan_declared()
# ═══════════════════════════════════════════════════════════════════════


class TestVerifyRetrievalPlanDeclared:
    def test_valid_plan_detected(self):
        response = (
            "<retrieval_plan>\n"
            "Using: mem-001, mem-002\n"
            "Reason: Both contain relevant information\n"
            "Confidence: 0.85\n"
            "</retrieval_plan>\n"
            "The answer is..."
        )
        assert verify_retrieval_plan_declared(response) is True

    def test_missing_plan_returns_false(self):
        response = "The answer is 42. No plan here."
        assert verify_retrieval_plan_declared(response) is False

    def test_only_open_tag_returns_false(self):
        response = "<retrieval_plan>something incomplete"
        assert verify_retrieval_plan_declared(response) is False

    def test_only_close_tag_returns_false(self):
        response = "something</retrieval_plan>"
        assert verify_retrieval_plan_declared(response) is False


# ═══════════════════════════════════════════════════════════════════════
# extract_declared_confidence()
# ═══════════════════════════════════════════════════════════════════════


class TestExtractDeclaredConfidence:
    def test_extracts_float(self):
        response = (
            "<retrieval_plan>\n"
            "Using: mem-001\n"
            "Reason: relevant\n"
            "Confidence: 0.75\n"
            "</retrieval_plan>"
        )
        assert extract_declared_confidence(response) == pytest.approx(0.75)

    def test_clips_to_zero_one(self):
        """Values outside [0,1] are clipped."""
        response = (
            "<retrieval_plan>Confidence: 1.5</retrieval_plan>"
        )
        val = extract_declared_confidence(response)
        assert val is not None
        assert val == pytest.approx(1.0)

    def test_missing_confidence_returns_none(self):
        response = "<retrieval_plan>Using: mem-001\nReason: relevant\n</retrieval_plan>"
        assert extract_declared_confidence(response) is None

    def test_no_plan_returns_none(self):
        assert extract_declared_confidence("No plan here.") is None

    def test_zero_confidence(self):
        response = "<retrieval_plan>Confidence: 0.0</retrieval_plan>"
        assert extract_declared_confidence(response) == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════
# check_confidence_consistency()
# ═══════════════════════════════════════════════════════════════════════


class TestCheckConfidenceConsistency:
    def test_consistent_when_within_tolerance(self):
        assert check_confidence_consistency(0.8, 0.75, tolerance=0.25) is True

    def test_inconsistent_when_beyond_tolerance(self):
        assert check_confidence_consistency(0.9, 0.2, tolerance=0.25) is False

    def test_exact_match_is_consistent(self):
        assert check_confidence_consistency(0.5, 0.5) is True

    def test_threshold_boundary_consistent(self):
        # Exactly at tolerance boundary
        assert check_confidence_consistency(0.5, 0.75, tolerance=0.25) is True

    def test_one_above_boundary_inconsistent(self):
        # Just over tolerance
        assert check_confidence_consistency(0.5, 0.76, tolerance=0.25) is False
