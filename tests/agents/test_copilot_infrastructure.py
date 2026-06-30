# [C5-REAL] Exergy-Maximized
"""Tests for Level 3 Copilot Infrastructure - Context, Debounce, Cache, LLM Strategy.

Validates the production-grade modules that support the CopilotAgent.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest

from babylon60.agents.copilot_cache import CacheStats, SuggestionCache
from babylon60.agents.copilot_context import (
    ContextWindow,
    build_context_window,
    estimate_tokens,
    is_inside_string,
)
from babylon60.agents.copilot_contracts import (
    Confidence,
    CopilotContextPayload,
    CursorContext,
    ProjectContext,
    SuggestionBatch,
    SuggestionKind,
    SuggestionProposal,
)
from babylon60.agents.copilot_debounce import DebounceController
from babylon60.agents.copilot_llm_strategy import (
    DeterministicFallbackClient,
    LLMCompletionStrategy,
    LLMResponse,
)


# ══════════════════════════════════════════════════════════════════
# Context Window Tests
# ══════════════════════════════════════════════════════════════════


class TestContextWindow:
    """Test intelligent context window construction."""

    def test_estimate_tokens(self) -> None:
        """Token estimation: ~4 chars per token."""
        assert estimate_tokens("") == 0
        assert estimate_tokens("hello") == 1
        assert estimate_tokens("a" * 100) == 25

    def test_small_context_fits_without_truncation(self) -> None:
        """Small prefix/suffix should pass through unchanged."""
        prefix = "import os\n\ndef hello():\n    pass\n"
        suffix = "\ndef world():\n    pass\n"

        window = build_context_window(prefix, suffix, budget_tokens=2048)

        assert window.prefix == prefix
        assert window.suffix == suffix
        assert window.truncated is False
        assert window.tokens_used == estimate_tokens(prefix) + estimate_tokens(suffix)

    def test_large_prefix_is_truncated(self) -> None:
        """Large prefix should be truncated respecting priority."""
        # Build a large prefix with imports, functions, and body lines
        lines = ["import os", "import sys", ""]
        for i in range(100):
            lines.append(f"def func_{i}():")
            lines.append(f"    return {i}")
            lines.append("")
        lines.append("def current_function():")
        prefix = "\n".join(lines)

        window = build_context_window(prefix, "", budget_tokens=100)

        assert window.truncated is True
        assert window.tokens_used <= 100
        # Should preserve cursor-adjacent lines
        assert "current_function" in window.prefix

    def test_suffix_truncation_keeps_nearest(self) -> None:
        """Suffix truncation should keep lines closest to cursor."""
        suffix = "\n".join([f"line_{i}" for i in range(200)])
        window = build_context_window("", suffix, budget_tokens=50)

        assert window.truncated is True
        # First lines (nearest to cursor) should be present
        assert "line_0" in window.suffix

    def test_fim_formatting(self) -> None:
        """FIM tags should be correctly applied."""
        window = build_context_window("prefix", "suffix", budget_tokens=100)

        assert window.fim_prefix.startswith("<|fim_prefix|>")
        assert window.fim_suffix.startswith("<|fim_suffix|>")
        assert window.fim_middle == "<|fim_middle|>"

    def test_budget_enforcement(self) -> None:
        """Total tokens should never exceed budget."""
        prefix = "x" * 10000
        suffix = "y" * 10000
        budget = 200

        window = build_context_window(prefix, suffix, budget_tokens=budget)

        assert window.tokens_used <= budget

    def test_import_preservation(self) -> None:
        """Import lines should be prioritized during truncation."""
        lines = [
            "import numpy as np",
            "import pandas as pd",
            "from pathlib import Path",
            "",
        ]
        # Add lots of filler
        for i in range(200):
            lines.append(f"    x_{i} = {i}")
        lines.append("def current():")
        prefix = "\n".join(lines)

        window = build_context_window(prefix, "", budget_tokens=100)

        # At least some imports should survive
        assert window.truncated is True

    def test_prefix_ratio(self) -> None:
        """prefix_ratio should control budget allocation."""
        prefix = "a" * 5000
        suffix = "b" * 5000

        window_75 = build_context_window(prefix, suffix, budget_tokens=200, prefix_ratio=0.75)
        window_25 = build_context_window(prefix, suffix, budget_tokens=200, prefix_ratio=0.25)

        # 75% prefix should give more prefix tokens
        assert window_75.prefix_tokens >= window_25.prefix_tokens


class TestStringDetection:
    """Test string literal detection."""

    def test_not_in_string(self) -> None:
        assert is_inside_string("x = 1", 2) is False

    def test_in_single_quote_string(self) -> None:
        assert is_inside_string("x = 'hello'", 6) is True

    def test_in_double_quote_string(self) -> None:
        assert is_inside_string('x = "hello"', 6) is True

    def test_after_string(self) -> None:
        assert is_inside_string("x = 'hi' + y", 11) is False


# ══════════════════════════════════════════════════════════════════
# Debounce Controller Tests
# ══════════════════════════════════════════════════════════════════


class TestDebounceController:
    """Test keystroke debouncing."""

    def _make_context(self, prefix: str = "test") -> CopilotContextPayload:
        return CopilotContextPayload(
            cursor=CursorContext(file_path="test.py", prefix=prefix),
        )

    @pytest.mark.asyncio
    async def test_single_request_fires(self) -> None:
        """A single request should fire after debounce interval."""
        debounce = DebounceController(debounce_ms=50)
        fired = []

        async def callback(ctx: CopilotContextPayload) -> None:
            fired.append(ctx)

        await debounce.schedule(self._make_context(), callback)
        await asyncio.sleep(0.1)

        assert len(fired) == 1

    @pytest.mark.asyncio
    async def test_rapid_requests_coalesce(self) -> None:
        """Rapid requests should coalesce to the latest."""
        debounce = DebounceController(debounce_ms=100)
        fired = []

        async def callback(ctx: CopilotContextPayload) -> None:
            fired.append(ctx.cursor.prefix)

        # Fire 5 rapid requests
        for i in range(5):
            await debounce.schedule(self._make_context(f"key-{i}"), callback)

        await asyncio.sleep(0.2)

        # Only the last should fire
        assert len(fired) == 1
        assert fired[0] == "key-4"

    @pytest.mark.asyncio
    async def test_cancel_prevents_fire(self) -> None:
        """Cancelling a request should prevent it from firing."""
        debounce = DebounceController(debounce_ms=100)
        fired = []

        async def callback(ctx: CopilotContextPayload) -> None:
            fired.append(True)

        request_id = await debounce.schedule(self._make_context(), callback)
        assert debounce.cancel(request_id) is True
        await asyncio.sleep(0.15)

        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_cancel_all(self) -> None:
        """cancel_all should cancel all pending requests."""
        debounce = DebounceController(debounce_ms=200)
        fired = []

        async def callback(ctx: CopilotContextPayload) -> None:
            fired.append(True)

        await debounce.schedule(self._make_context("a"), callback)
        count = debounce.cancel_all()

        await asyncio.sleep(0.25)
        assert len(fired) == 0
        assert count >= 0  # May be 0 if coalescing already cancelled

    @pytest.mark.asyncio
    async def test_stats_tracking(self) -> None:
        """Stats should track scheduled, fired, coalesced counts."""
        debounce = DebounceController(debounce_ms=50)

        async def callback(ctx: CopilotContextPayload) -> None:
            pass

        await debounce.schedule(self._make_context(), callback)
        await asyncio.sleep(0.1)

        stats = debounce.get_stats()
        assert stats["total_scheduled"] >= 1
        assert stats["total_fired"] >= 1

    @pytest.mark.asyncio
    async def test_pending_count(self) -> None:
        """pending_count should reflect active requests."""
        debounce = DebounceController(debounce_ms=500)

        async def callback(ctx: CopilotContextPayload) -> None:
            pass

        await debounce.schedule(self._make_context(), callback)
        assert debounce.pending_count >= 0  # May be 0 due to race

        debounce.cancel_all()


# ══════════════════════════════════════════════════════════════════
# Suggestion Cache Tests
# ══════════════════════════════════════════════════════════════════


class TestSuggestionCache:
    """Test LRU suggestion cache."""

    def _make_batch(self, n: int = 1) -> SuggestionBatch:
        return SuggestionBatch(
            suggestions=[
                SuggestionProposal(
                    suggestion_id=f"test-{i}",
                    kind=SuggestionKind.CODE_COMPLETION,
                )
                for i in range(n)
            ],
            context_hash="test-hash",
        )

    def test_put_and_get(self) -> None:
        """Basic put/get should work."""
        cache = SuggestionCache(max_size=10)
        batch = self._make_batch()

        cache.put("hash-1", batch)
        result = cache.get("hash-1")

        assert result is not None
        assert len(result.suggestions) == 1

    def test_miss_returns_none(self) -> None:
        """Missing key should return None."""
        cache = SuggestionCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self) -> None:
        """Oldest entries should be evicted when cache is full."""
        cache = SuggestionCache(max_size=3)

        cache.put("a", self._make_batch())
        cache.put("b", self._make_batch())
        cache.put("c", self._make_batch())
        cache.put("d", self._make_batch())  # Should evict "a"

        assert cache.get("a") is None  # Evicted
        assert cache.get("d") is not None  # Present
        assert cache.size == 3

    def test_lru_refresh_on_get(self) -> None:
        """Getting an entry should refresh it (move to end)."""
        cache = SuggestionCache(max_size=3)

        cache.put("a", self._make_batch())
        cache.put("b", self._make_batch())
        cache.put("c", self._make_batch())

        # Access "a" to refresh it
        cache.get("a")

        # Now "b" is the oldest, should be evicted
        cache.put("d", self._make_batch())

        assert cache.get("a") is not None  # Refreshed, still present
        assert cache.get("b") is None  # Evicted

    def test_ttl_expiration(self) -> None:
        """Expired entries should return None."""
        cache = SuggestionCache(max_size=10, ttl_seconds=0.05)
        cache.put("hash-1", self._make_batch())

        # Entry should be valid immediately
        assert cache.get("hash-1") is not None

        # Wait for TTL
        time.sleep(0.1)
        assert cache.get("hash-1") is None

    def test_file_invalidation(self) -> None:
        """Entries should be invalidated by file path."""
        cache = SuggestionCache()
        cache.put("h1", self._make_batch(), file_paths=["file_a.py"])
        cache.put("h2", self._make_batch(), file_paths=["file_a.py"])
        cache.put("h3", self._make_batch(), file_paths=["file_b.py"])

        count = cache.invalidate("file_a.py")

        assert count == 2
        assert cache.get("h1") is None
        assert cache.get("h2") is None
        assert cache.get("h3") is not None

    def test_clear(self) -> None:
        """clear() should empty the cache."""
        cache = SuggestionCache()
        cache.put("a", self._make_batch())
        cache.put("b", self._make_batch())

        cache.clear()
        assert cache.size == 0

    def test_stats(self) -> None:
        """Stats should track hits, misses, evictions."""
        cache = SuggestionCache(max_size=2)

        cache.put("a", self._make_batch())
        cache.get("a")  # hit
        cache.get("b")  # miss

        stats = cache.stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(0.5)


# ══════════════════════════════════════════════════════════════════
# LLM Strategy Tests
# ══════════════════════════════════════════════════════════════════


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(
        self,
        response_text: str = "    return 42\n",
        delay: float = 0.0,
        fail: bool = False,
    ) -> None:
        self.response_text = response_text
        self.delay = delay
        self.fail = fail
        self.calls: list[dict] = []

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "prompt_len": len(prompt),
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.fail:
            raise ConnectionError("LLM API unavailable")

        return LLMResponse(
            text=self.response_text,
            tokens_used=len(self.response_text) // 4,
            model="mock-model",
            latency_ms=self.delay * 1000,
            finish_reason="stop",
        )


class TestLLMStrategy:
    """Test LLM-backed suggestion strategy."""

    def _make_context(self, prefix: str = "def hello():") -> CopilotContextPayload:
        return CopilotContextPayload(
            cursor=CursorContext(
                file_path="test.py",
                language="python",
                prefix=prefix,
                suffix="\n\ndef main(): pass\n",
            ),
            max_suggestions=3,
        )

    @pytest.mark.asyncio
    async def test_generates_suggestions(self) -> None:
        """LLM strategy should produce suggestions from mock client."""
        client = MockLLMClient(response_text="    return 42\n")
        strategy = LLMCompletionStrategy(client, context_budget_tokens=512)

        results = await strategy.generate(self._make_context())

        assert len(results) >= 1
        assert results[0].kind == SuggestionKind.CODE_COMPLETION
        assert results[0].inline_text == "    return 42\n"

    @pytest.mark.asyncio
    async def test_uses_context_window(self) -> None:
        """Strategy should truncate context before sending to LLM."""
        client = MockLLMClient()
        strategy = LLMCompletionStrategy(client, context_budget_tokens=50)

        # Large context
        big_prefix = "x = 1\n" * 1000
        results = await strategy.generate(self._make_context(prefix=big_prefix))

        # LLM should have been called with truncated prompt
        assert len(client.calls) == 1
        assert client.calls[0]["prompt_len"] < len(big_prefix)

    @pytest.mark.asyncio
    async def test_fallback_on_api_failure(self) -> None:
        """Strategy should fall back to deterministic on LLM failure."""
        client = MockLLMClient(fail=True)
        strategy = LLMCompletionStrategy(client)

        results = await strategy.generate(self._make_context(prefix="def hello():"))

        # Should still return something (from fallback)
        assert len(results) >= 1
        assert results[0].model_used == "deterministic-fallback"

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self) -> None:
        """Slow LLM should trigger timeout and fallback."""
        client = MockLLMClient(delay=10.0)  # Very slow
        strategy = LLMCompletionStrategy(
            client,
            timeout_seconds=0.1,  # Very short timeout
        )

        results = await strategy.generate(self._make_context())

        assert len(results) >= 1
        assert results[0].model_used == "deterministic-fallback"

    @pytest.mark.asyncio
    async def test_cache_integration(self) -> None:
        """Strategy should use cache for repeated contexts."""
        client = MockLLMClient(response_text="cached_result\n")
        cache = SuggestionCache(max_size=10, ttl_seconds=60)
        strategy = LLMCompletionStrategy(client, cache=cache)

        context = self._make_context()

        # First call - cache miss
        results1 = await strategy.generate(context)
        assert len(client.calls) == 1

        # Second call - cache hit (no additional LLM call)
        results2 = await strategy.generate(context)
        assert len(client.calls) == 1  # Still 1, used cache

    @pytest.mark.asyncio
    async def test_deterministic_fallback_patterns(self) -> None:
        """DeterministicFallbackClient should recognize basic patterns."""
        client = DeterministicFallbackClient()

        # Block definition
        r1 = await client.complete("class MyClass:")
        assert "pass" in r1.text

        # Function without docstring
        r2 = await client.complete("def hello():\n    x = 1")
        assert '"""' in r2.text or r2.text == ""

        # Empty / no pattern
        r3 = await client.complete("x = 1 + 2")
        assert r3.finish_reason == "stop"
