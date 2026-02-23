"""Tests for cortex.consensus.byzantine — WBFT Consensus."""

from __future__ import annotations

import pytest

from cortex.consensus.byzantine import ByzantineVerdict, ResponseTrust, WBFTConsensus
from cortex.thinking.fusion_models import ModelResponse, ThinkingHistory


def _make_response(
    provider: str, model: str, content: str, *, error: str | None = None
) -> ModelResponse:
    return ModelResponse(
        provider=provider,
        model=model,
        content=content,
        latency_ms=100.0,
        error=error,
    )


@pytest.fixture
def wbft() -> WBFTConsensus:
    return WBFTConsensus()


class TestByzantineVerdictModel:
    def test_fault_tolerance(self):
        v = ByzantineVerdict()
        assert v.fault_tolerance == 0

    def test_best_response_empty(self):
        v = ByzantineVerdict()
        assert v.best_response() is None


class TestResponseTrustModel:
    def test_label(self):
        r = _make_response("openai", "gpt-4o", "test")
        rt = ResponseTrust(
            response=r,
            trust_score=0.9,
            reputation=0.8,
            vote_multiplier=1.0,
            is_trusted=True,
            is_outlier=False,
            agreement_with_centroid=0.85,
        )
        assert rt.label == "openai:gpt-4o"


class TestWBFTNoQuorum:
    def test_single_response(self, wbft: WBFTConsensus):
        responses = [_make_response("openai", "gpt-4o", "The answer is 42.")]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 1
        assert not verdict.quorum_met  # Can't reach quorum with 1

    def test_all_errors(self, wbft: WBFTConsensus):
        responses = [
            _make_response("openai", "gpt-4o", "", error="timeout"),
            _make_response("anthropic", "claude", "", error="rate limit"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 0
        assert verdict.confidence == pytest.approx(0.0)


class TestWBFTAgreement:
    def test_full_agreement(self, wbft: WBFTConsensus):
        """3 models giving similar responses → all trusted, high confidence."""
        responses = [
            _make_response("openai", "gpt-4o", "Python is a programming language"),
            _make_response(
                "anthropic", "claude", "Python is a general-purpose programming language"
            ),
            _make_response("gemini", "2.0-flash", "Python is a popular programming language"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 3
        assert verdict.confidence > 0.5
        assert verdict.quorum_met

    def test_one_outlier(self, wbft: WBFTConsensus):
        """2 agree, 1 diverges → outlier detected."""
        responses = [
            _make_response(
                "openai",
                "gpt-4o",
                "Machine learning uses neural networks and gradient descent for optimization",
            ),
            _make_response(
                "anthropic",
                "claude",
                "Machine learning uses neural networks for training models with gradient descent",
            ),
            _make_response(
                "deepseek",
                "v3",
                "The weather in Tokyo is sunny with temperatures around 25 degrees Celsius",
            ),
        ]
        verdict = wbft.evaluate(responses)
        # The wildly divergent response should be flagged
        assert len(verdict.outliers) >= 1
        outlier_labels = {o.label for o in verdict.outliers}
        assert "deepseek:v3" in outlier_labels

    def test_best_response(self, wbft: WBFTConsensus):
        """best_response should return the most trusted response."""
        responses = [
            _make_response("openai", "gpt-4o", "Python uses indentation for syntax blocks"),
            _make_response("anthropic", "claude", "Python uses indentation to define code blocks"),
            _make_response("gemini", "2.0-flash", "Python uses whitespace indentation for blocks"),
        ]
        verdict = wbft.evaluate(responses)
        best = verdict.best_response()
        assert best is not None
        assert best.ok

    def test_fault_tolerance_with_five(self, wbft: WBFTConsensus):
        """With 5 responses, should tolerate 1 faulty (⌊(5-1)/3⌋ = 1)."""
        responses = [
            _make_response("openai", "gpt-4o", "Rust is a systems programming language"),
            _make_response("anthropic", "claude", "Rust is a systems-level programming language"),
            _make_response(
                "gemini", "2.0-flash", "Rust is a compiled systems programming language"
            ),
            _make_response("deepseek", "v3", "Rust is a fast systems programming language"),
            _make_response("xai", "grok-2", "The recipe for chocolate cake requires cocoa"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.fault_tolerance == 1
        assert verdict.trusted_count >= 3


class TestWBFTWithHistory:
    def test_reputation_weighting(self, wbft: WBFTConsensus):
        """Models with higher win rate should have more weight in consensus."""
        from cortex.thinking.fusion_models import FusedThought, FusionStrategy

        history = ThinkingHistory()
        # Record openai as consistent winner
        for _ in range(10):
            history.record(
                FusedThought(
                    content="test",
                    strategy=FusionStrategy.MAJORITY,
                    confidence=0.9,
                    sources=[
                        ModelResponse(
                            provider="openai", model="gpt-4o", content="win", latency_ms=100
                        ),
                        ModelResponse(provider="bad", model="v1", content="lose", latency_ms=200),
                    ],
                    meta={"winner": "openai:gpt-4o"},
                )
            )

        responses = [
            _make_response("openai", "gpt-4o", "Correct answer about quantum computing"),
            _make_response("anthropic", "claude", "Correct answer about quantum computing theory"),
            _make_response("bad", "v1", "Completely wrong irrelevant answer about cooking"),
        ]

        verdict = wbft.evaluate(responses, history=history)
        # openai should have higher reputation
        openai_trust = next(a for a in verdict.all_assessments if a.label == "openai:gpt-4o")
        bad_trust = next(a for a in verdict.all_assessments if a.label == "bad:v1")
        assert openai_trust.reputation > bad_trust.reputation


class TestWBFTEdgeCases:
    def test_identical_responses(self, wbft: WBFTConsensus):
        """Identical responses → perfect agreement."""
        same = "The mitochondria is the powerhouse of the cell."
        responses = [
            _make_response("openai", "gpt-4o", same),
            _make_response("anthropic", "claude", same),
            _make_response("gemini", "2.0-flash", same),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 3
        assert verdict.confidence > 0.7

    def test_two_models_both_trusted(self, wbft: WBFTConsensus):
        """With 2 agreeing models, both should be trusted."""
        responses = [
            _make_response("openai", "gpt-4o", "TypeScript adds static types to JavaScript"),
            _make_response(
                "anthropic", "claude", "TypeScript provides static typing for JavaScript"
            ),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 2

    def test_mixed_ok_and_errors(self, wbft: WBFTConsensus):
        """Errored responses should not affect consensus of valid ones."""
        responses = [
            _make_response("openai", "gpt-4o", "Docker containerizes applications"),
            _make_response("anthropic", "claude", "Docker containers package applications"),
            _make_response("broken", "v1", "", error="500 Internal Server Error"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 2
        # Error response should be in assessments but not trusted
        assert verdict.total_count == 3
