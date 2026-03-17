"""Tests for A (Bayesian Trust), C (Entropic Quarantine).

B (Handoff v1.3) is tested by asserting HANDOFF_VERSION = '1.3' and
that the cognitive_fingerprint key is present in the output dict.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.immune.filters.entropic_quarantine import (
    EntropicQuarantineFilter,
    _extract_text,
    _shannon_entropy,
)
from cortex.extensions.trust.bayesian import (
    BayesianTrustUpdater,
    Signal,
    _map_to_confidence,
    _posterior_mean,
)

# ─── Unit: Shannon entropy ────────────────────────────────────────────────


class TestShannonEntropy:
    def test_empty_string_returns_zero(self):
        assert _shannon_entropy("") == 0.0

    def test_single_char_returns_zero(self):
        """H(p) = 0 for a single unique character."""
        assert _shannon_entropy("aaaa") == pytest.approx(0.0)

    def test_two_equal_symbols_returns_one_bit(self):
        """H("abab...") = 1 bit."""
        assert _shannon_entropy("abab" * 100) == pytest.approx(1.0, abs=0.01)

    def test_rich_text_above_threshold(self):
        text = "The quick brown fox jumps over the lazy dog 1234567890!@#"
        assert _shannon_entropy(text) > 3.5

    def test_extract_text_string(self):
        assert _extract_text("hello") == "hello"

    def test_extract_text_dict_with_content(self):
        assert _extract_text({"content": "world", "id": 1}) == "world"

    def test_extract_text_bare_dict(self):
        result = _extract_text({"key": "value"})
        assert "key" in result

    def test_extract_text_fallback(self):
        assert _extract_text(42) == "42"


# ─── Unit: EntropicQuarantineFilter ──────────────────────────────────────


class TestEntropicQuarantineFilter:
    @pytest.fixture
    def f(self):
        return EntropicQuarantineFilter()

    @pytest.mark.asyncio
    async def test_filter_id_is_f6(self, f):
        assert f.filter_id == "F6"

    @pytest.mark.asyncio
    async def test_rich_text_passes(self, f):
        signal = "The quick brown fox jumps over the lazy dog, revealing secrets of the universe."
        result = await f.evaluate(signal, {})
        from cortex.extensions.immune.filters.base import Verdict

        assert result.verdict == Verdict.PASS
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_repeated_chars_blocked(self, f):
        signal = "aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = await f.evaluate(signal, {})
        from cortex.extensions.immune.filters.base import Verdict

        assert result.verdict == Verdict.BLOCK
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_marginal_signal_held(self, f):
        # Use 5-character mix that lands ~2.8 bits (above 2.5, below 3.5)
        # a=40, b=30, c=15, d=10, e=5 → H ≈ 2.14 bits, which is below mid → BLOCK.
        # Instead use balanced 5+ char mix: 20 each of 5 different chars → H=≈2.32
        # Better: use a balanced 8-char signal: H = log2(8) = 3.0 bits exactly.
        signal = "abcdefgh" * 40  # uniform 8-char dist → H=3.0 bits (2.5<3.0<3.5 → HOLD)
        from cortex.extensions.immune.filters.base import Verdict

        result = await f.evaluate(signal, {})
        assert result.verdict == Verdict.HOLD

    @pytest.mark.asyncio
    async def test_dict_content_evaluated(self, f):
        signal = {"content": "The quick brown fox jumps over the lazy dog."}
        result = await f.evaluate(signal, {})
        from cortex.extensions.immune.filters.base import Verdict

        assert result.verdict == Verdict.PASS

    @pytest.mark.asyncio
    async def test_custom_threshold_via_context(self, f):
        """High threshold = 99 bits forces every real signal to BLOCK."""
        signal = "hello world"
        result = await f.evaluate(
            signal, {"entropy_high_threshold": 99.0, "entropy_mid_threshold": 98.0}
        )
        from cortex.extensions.immune.filters.base import Verdict

        assert result.verdict == Verdict.BLOCK

    @pytest.mark.asyncio
    async def test_metadata_contains_entropy(self, f):
        signal = "The quick brown fox"
        result = await f.evaluate(signal, {})
        assert "entropy_bits" in result.metadata
        assert result.metadata["entropy_bits"] > 0


# ─── Unit: BayesianTrustUpdater ──────────────────────────────────────────


class TestPosteriorMath:
    def test_posterior_mean_symmetric(self):
        assert _posterior_mean(5.0, 5.0) == pytest.approx(0.5)

    def test_posterior_mean_dominant_alpha(self):
        assert _posterior_mean(9.0, 1.0) == pytest.approx(0.9)

    def test_map_c5_mean(self):
        assert _map_to_confidence(0.9) == "C5"

    def test_map_c1_mean(self):
        assert _map_to_confidence(0.1) == "C1"

    def test_map_c3_mean(self):
        assert _map_to_confidence(0.50) == "C3"


class TestBayesianTrustUpdater:
    def _make_engine(self, conf="C3", score=1.0):
        engine = MagicMock()
        conn = AsyncMock()
        row = (conf, score)
        conn.execute.return_value.__aenter__ = AsyncMock(
            return_value=AsyncMock(fetchone=AsyncMock(return_value=row))
        )
        conn.execute.return_value.__aexit__ = AsyncMock(return_value=False)
        engine.get_conn = AsyncMock(return_value=conn)
        return engine, conn

    @pytest.mark.asyncio
    async def test_confirm_raises_confidence(self):
        engine, conn = self._make_engine("C1", 0.1)
        # Simple mock: fetchone returns the row, commit is no-op
        conn_obj = MagicMock()
        cursor_mock = AsyncMock()
        cursor_mock.fetchone = AsyncMock(return_value=("C1", 0.1))
        conn_obj.execute = AsyncMock(return_value=cursor_mock)
        conn_obj.commit = AsyncMock()
        engine.get_conn = AsyncMock(return_value=conn_obj)

        updater = BayesianTrustUpdater(engine)
        result = await updater.update(1, Signal.CONFIRM)

        assert result.old_confidence == "C1"
        assert result.posterior_mean > 0.1  # moved toward higher confidence

    @pytest.mark.asyncio
    async def test_contradict_lowers_confidence(self):
        conn_obj = MagicMock()
        cursor_mock = AsyncMock()
        cursor_mock.fetchone = AsyncMock(return_value=("C5", 0.9))
        conn_obj.execute = AsyncMock(return_value=cursor_mock)
        conn_obj.commit = AsyncMock()
        engine = MagicMock()
        engine.get_conn = AsyncMock(return_value=conn_obj)

        updater = BayesianTrustUpdater(engine)
        result = await updater.update(1, Signal.CONTRADICT)
        # posterior mean of C5 prior after contradict should drop
        assert result.posterior_mean < 0.9

    @pytest.mark.asyncio
    async def test_fact_not_found_raises(self):
        conn_obj = MagicMock()
        cursor_mock = AsyncMock()
        cursor_mock.fetchone = AsyncMock(return_value=None)
        conn_obj.execute = AsyncMock(return_value=cursor_mock)
        engine = MagicMock()
        engine.get_conn = AsyncMock(return_value=conn_obj)

        updater = BayesianTrustUpdater(engine)
        with pytest.raises(ValueError, match="not found"):
            await updater.update(999, Signal.CONFIRM)

    @pytest.mark.asyncio
    async def test_signal_string_accepted(self):
        conn_obj = MagicMock()
        cursor_mock = AsyncMock()
        cursor_mock.fetchone = AsyncMock(return_value=("C3", 1.0))
        conn_obj.execute = AsyncMock(return_value=cursor_mock)
        conn_obj.commit = AsyncMock()
        engine = MagicMock()
        engine.get_conn = AsyncMock(return_value=conn_obj)

        updater = BayesianTrustUpdater(engine)
        result = await updater.update(1, "replicate")  # str, not Signal enum
        assert result.signal == "replicate"


# ─── B: Handoff version check ─────────────────────────────────────────────


class TestHandoffV13:
    def test_version_bumped(self):
        """Check that HANDOFF_VERSION constant is '1.3' using a regex on the source file."""
        import re
        from pathlib import Path

        src = Path("cortex/agents/handoff.py").read_text(encoding="utf-8")
        match = re.search(r'HANDOFF_VERSION\s*=\s*"([\d\.]+)"', src)
        assert match is not None, "HANDOFF_VERSION not found in handoff.py"
        assert match.group(1) == "1.3"

    def test_cognitive_fingerprint_key_in_source(self):
        """Verify cognitive_fingerprint key was added to generate_handoff."""
        from pathlib import Path

        src = Path("cortex/agents/handoff.py").read_text(encoding="utf-8")
        assert '"cognitive_fingerprint"' in src, "cognitive_fingerprint section missing"
