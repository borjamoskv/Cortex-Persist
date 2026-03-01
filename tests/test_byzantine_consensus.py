"""Unit tests for WBFT (Weighted Byzantine Fault Tolerance).

Tests the WBFTConsensus engine and ByzantineVerdict data model
using synthetic ModelResponse objects — no DB, no API.
"""

from __future__ import annotations

from cortex.consensus.byzantine import ByzantineVerdict, ResponseTrust, WBFTConsensus
from cortex.thinking.fusion_models import ModelResponse

# ─── Helpers ─────────────────────────────────────────────────────────


def _make_response(
    label: str, content: str, error: str | None = None,
) -> ModelResponse:
    """Create a ModelResponse using provider:model split from label."""
    parts = label.split(":", 1)
    provider = parts[0]
    model = parts[1] if len(parts) > 1 else parts[0]
    return ModelResponse(
        provider=provider,
        model=model,
        content=content,
        latency_ms=100.0,
        error=error,
        token_count=len(content.split()),
    )


# ─── Core WBFT Tests ─────────────────────────────────────────────────


class TestWBFTConsensus:
    def test_all_agree(self):
        """3 identical responses → all should be trusted."""
        wbft = WBFTConsensus(min_responses=2)
        responses = [
            _make_response("a:model-a", "The answer is 42"),
            _make_response("b:model-b", "The answer is 42"),
            _make_response("c:model-c", "The answer is 42"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.trusted_count == 3
        assert len(verdict.outliers) == 0
        assert verdict.confidence > 0.5

    def test_one_outlier(self):
        """2 agree, 1 completely different → outlier detected."""
        wbft = WBFTConsensus(min_responses=2, outlier_threshold=0.2)
        responses = [
            _make_response("a:model-a", "The capital of France is Paris"),
            _make_response("b:model-b", "The capital of France is Paris"),
            _make_response(
                "c:model-c",
                "Quantum entanglement defies classical physics completely",
            ),
        ]
        verdict = wbft.evaluate(responses)
        assert len(verdict.outliers) >= 1
        outlier_labels = {o.label for o in verdict.outliers}
        assert "c:model-c" in outlier_labels

    def test_below_min_responses(self):
        """Single response → fast path, no full consensus."""
        wbft = WBFTConsensus(min_responses=2)
        verdict = wbft.evaluate([_make_response("a:model-a", "Hello")])
        assert verdict.quorum_met is False
        assert verdict.confidence == 0.5
        assert verdict.trusted_count == 1

    def test_no_valid_responses(self):
        """All responses errored → confidence 0."""
        wbft = WBFTConsensus(min_responses=2)
        responses = [
            _make_response("a:model-a", "", error="timeout"),
            _make_response("b:model-b", "", error="timeout"),
        ]
        verdict = wbft.evaluate(responses)
        assert verdict.confidence == 0.0
        assert verdict.quorum_met is False

    def test_error_responses_appended(self):
        """Error responses should appear in all_assessments as untrusted."""
        wbft = WBFTConsensus(min_responses=2)
        responses = [
            _make_response("a:model-a", "The answer is 42"),
            _make_response("b:model-b", "The answer is 42"),
            _make_response("err:model-err", "", error="timeout"),
        ]
        verdict = wbft.evaluate(responses)
        err_assessments = [
            a for a in verdict.all_assessments
            if a.label == "err:model-err"
        ]
        assert len(err_assessments) == 1
        assert err_assessments[0].is_trusted is False
        assert err_assessments[0].trust_score == 0.0


# ─── ByzantineVerdict Tests ──────────────────────────────────────────


class TestByzantineVerdict:
    def test_fault_tolerance(self):
        """Fault tolerance = (n-1) // 3."""
        verdict = ByzantineVerdict()
        assert verdict.fault_tolerance == 0

        # Simulate 4 assessments
        dummy = _make_response("x:y", "content")
        trust = ResponseTrust(
            response=dummy,
            trust_score=0.9,
            reputation=0.5,
            vote_multiplier=1.0,
            is_trusted=True,
            is_outlier=False,
            agreement_with_centroid=0.9,
        )
        verdict.all_assessments = [trust] * 4
        assert verdict.fault_tolerance == 1

        verdict.all_assessments = [trust] * 7
        assert verdict.fault_tolerance == 2

    def test_best_response_none_when_empty(self):
        verdict = ByzantineVerdict()
        assert verdict.best_response() is None

    def test_best_response_selection(self):
        """Best response = highest trust_score × reputation."""
        r1 = _make_response("low:model", "content1")
        r2 = _make_response("high:model", "content2")
        verdict = ByzantineVerdict(
            trusted_responses=[
                ResponseTrust(
                    response=r1,
                    trust_score=0.5,
                    reputation=0.3,
                    vote_multiplier=1.0,
                    is_trusted=True,
                    is_outlier=False,
                    agreement_with_centroid=0.5,
                ),
                ResponseTrust(
                    response=r2,
                    trust_score=0.9,
                    reputation=0.8,
                    vote_multiplier=1.0,
                    is_trusted=True,
                    is_outlier=False,
                    agreement_with_centroid=0.9,
                ),
            ],
        )
        best = verdict.best_response()
        assert best is not None
        assert best.label == "high:model"
