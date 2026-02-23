"""Tests for cortex.thinking.semantic_router — Semantic Routing."""

from __future__ import annotations

import pytest

from cortex.thinking.presets import ThinkingMode
from cortex.thinking.semantic_router import RouteDecision, SemanticRouter


@pytest.fixture
def router() -> SemanticRouter:
    return SemanticRouter()


class TestRouteDecision:
    def test_repr(self):
        d = RouteDecision(mode=ThinkingMode.CODE, confidence=0.85, reason="test")
        assert "code" in repr(d)
        assert "0.85" in repr(d)


class TestSemanticRouterCode:
    def test_code_with_file_reference(self, router: SemanticRouter):
        decision = router.classify("Fix the bug in auth.py where tokens expire")
        assert decision.mode == ThinkingMode.CODE
        assert decision.confidence > 0.5

    def test_code_with_keywords(self, router: SemanticRouter):
        decision = router.classify(
            "Refactor the function to use async await with proper error handling"
        )
        assert decision.mode == ThinkingMode.CODE

    def test_code_with_block(self, router: SemanticRouter):
        decision = router.classify("Fix this:\n```python\ndef foo():\n  pass\n```")
        assert decision.mode == ThinkingMode.CODE

    def test_code_with_import_pattern(self, router: SemanticRouter):
        decision = router.classify("from cortex.engine import CortexEngine and add a test")
        assert decision.mode == ThinkingMode.CODE


class TestSemanticRouterCreative:
    def test_creative_brainstorm(self, router: SemanticRouter):
        decision = router.classify("Brainstorm creative naming ideas for the new brand")
        assert decision.mode == ThinkingMode.CREATIVE

    def test_creative_imagine(self, router: SemanticRouter):
        decision = router.classify("Imagine a world where AI designs its own hardware")
        assert decision.mode == ThinkingMode.CREATIVE


class TestSemanticRouterReasoning:
    def test_reasoning_why(self, router: SemanticRouter):
        decision = router.classify(
            "Why does the architecture use event sourcing instead of CRUD? "
            "Analyze the tradeoffs and implications for scalability."
        )
        assert decision.mode == ThinkingMode.DEEP_REASONING

    def test_reasoning_comparison(self, router: SemanticRouter):
        decision = router.classify(
            "Compare the pros and cons of monorepo vs polyrepo strategy "
            "for our organization considering long-term consequences"
        )
        assert decision.mode == ThinkingMode.DEEP_REASONING


class TestSemanticRouterSpeed:
    def test_speed_short_question(self, router: SemanticRouter):
        decision = router.classify("What is WASM?")
        assert decision.mode == ThinkingMode.SPEED

    def test_speed_yes_no(self, router: SemanticRouter):
        decision = router.classify("Yes")
        assert decision.mode == ThinkingMode.SPEED


class TestSemanticRouterEdgeCases:
    def test_empty_prompt(self, router: SemanticRouter):
        decision = router.classify("")
        assert decision.mode == ThinkingMode.SPEED
        assert decision.confidence == pytest.approx(0.5)

    def test_whitespace_only(self, router: SemanticRouter):
        decision = router.classify("   ")
        assert decision.mode == ThinkingMode.SPEED

    def test_mixed_signals_code_wins(self, router: SemanticRouter):
        """When prompt has both code and reasoning signals, code should win."""
        decision = router.classify(
            "Analyze why the import fails in router.py and refactor the function"
        )
        assert decision.mode == ThinkingMode.CODE

    def test_batch_classify(self, router: SemanticRouter):
        prompts = ["Fix bug in auth.py", "Imagine a new world", "What is WASM?"]
        decisions = router.classify_batch(prompts)
        assert len(decisions) == 3
        assert decisions[0].mode == ThinkingMode.CODE
        assert decisions[2].mode == ThinkingMode.SPEED

    def test_signals_present(self, router: SemanticRouter):
        decision = router.classify("Refactor the database schema migration")
        assert "code" in decision.signals
        assert "creative" in decision.signals
        assert "reasoning" in decision.signals
        assert "speed" in decision.signals


class TestSemanticRouterSpanish:
    def test_spanish_code(self, router: SemanticRouter):
        decision = router.classify("Corregir el error en el test y refactorizar")
        assert decision.mode == ThinkingMode.CODE

    def test_spanish_creative(self, router: SemanticRouter):
        decision = router.classify("Imagina y genera una idea para un nuevo concepto")
        assert decision.mode == ThinkingMode.CREATIVE
