"""Unit tests for cortex.wealth.growth — GrowthEngine.

No DB, no IO. Tests deduplication, sorting, and configurability.
"""

from __future__ import annotations

import pytest

from cortex.extensions.wealth.growth import GrowthEngine, GrowthSignal

# ── Sorting ──────────────────────────────────────────────────────────


class TestPulseScan:
    @pytest.mark.asyncio
    async def test_sorted_by_alpha_score(self):
        engine = GrowthEngine()
        results = await engine.pulse_scan("CORTEX agent memory")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].alpha_score >= results[i + 1].alpha_score

    @pytest.mark.asyncio
    async def test_returns_signals(self):
        engine = GrowthEngine()
        results = await engine.pulse_scan("CORTEX")
        assert len(results) > 0
        assert all(isinstance(s, GrowthSignal) for s in results)


# ── Deduplication ────────────────────────────────────────────────────


class TestDeduplication:
    def test_dedup_keeps_highest_score(self):
        signals = [
            GrowthSignal(
                platform="github",
                target_url="https://example.com/issue/1",
                topic="Duplicate A",
                urgency_score=5.0,
                relevance_score=5.0,
                alpha_score=5.0,
                suggested_action="low",
            ),
            GrowthSignal(
                platform="reddit",
                target_url="https://example.com/issue/1",  # Same URL
                topic="Duplicate B",
                urgency_score=9.0,
                relevance_score=9.0,
                alpha_score=9.0,
                suggested_action="high",
            ),
        ]
        result = GrowthEngine._deduplicate(signals)
        assert len(result) == 1
        assert result[0].alpha_score == 9.0

    def test_dedup_different_urls_kept(self):
        signals = [
            GrowthSignal(
                platform="github",
                target_url="https://example.com/a",
                topic="A",
                urgency_score=5.0,
                relevance_score=5.0,
                alpha_score=5.0,
                suggested_action="do A",
            ),
            GrowthSignal(
                platform="github",
                target_url="https://example.com/b",
                topic="B",
                urgency_score=6.0,
                relevance_score=6.0,
                alpha_score=6.0,
                suggested_action="do B",
            ),
        ]
        result = GrowthEngine._deduplicate(signals)
        assert len(result) == 2


# ── Configurable channels ───────────────────────────────────────────


class TestChannels:
    @pytest.mark.asyncio
    async def test_custom_channels(self):
        engine = GrowthEngine(channels=("github",))
        results = await engine.pulse_scan("test")
        # Only github scanner runs, so all should be github
        assert all(s.platform == "github" for s in results)

    @pytest.mark.asyncio
    async def test_empty_channels(self):
        engine = GrowthEngine(channels=())
        results = await engine.pulse_scan("test")
        assert results == []


# ── GrowthSignal repr ────────────────────────────────────────────────


class TestGrowthSignalRepr:
    def test_repr_contains_platform_and_score(self):
        s = GrowthSignal(
            platform="github",
            target_url="https://example.com",
            topic="Test signal topic for repr",
            urgency_score=5.0,
            relevance_score=5.0,
            alpha_score=7.5,
            suggested_action="test",
        )
        r = repr(s)
        assert "github" in r
        assert "7.50" in r
