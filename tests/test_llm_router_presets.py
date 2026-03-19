"""Permanent pytest tests for LLM Router cost/tier-aware routing.

Covers:
- Preset loading (tier, cost_class, intent_model_map)
- BaseProvider tier/cost defaults
- LLMProvider preset-sourced tier/cost
- Router cost-aware fallback ordering
- Tier tiebreaking within same cost class
- Model policy validation (no prohibited patterns)
- Query APIs (get_providers_by_tier, get_providers_by_cost)
"""

from __future__ import annotations

import os

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault("DASHSCOPE_API_KEY", "test")

import pytest

from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm._presets import (
    _PRESETS_CACHE,
    get_providers_by_cost,
    get_providers_by_tier,
    load_presets,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear preset cache before each test."""
    _PRESETS_CACHE.clear()
    yield
    _PRESETS_CACHE.clear()


# ─── Preset Loading ──────────────────────────────────────────────────


class TestPresetLoading:
    """llm_presets.json loads correctly with all fields."""

    def test_loads_all_providers(self):
        presets = load_presets()
        assert len(presets) >= 25

    def test_every_provider_has_tier(self):
        presets = load_presets()
        for name, cfg in presets.items():
            assert "tier" in cfg, f"{name} missing tier"

    def test_every_provider_has_cost_class(self):
        presets = load_presets()
        for name, cfg in presets.items():
            assert "cost_class" in cfg, f"{name} missing cost_class"

    def test_tier_values_valid(self):
        valid = {"frontier", "high", "local"}
        presets = load_presets()
        for name, cfg in presets.items():
            assert cfg["tier"] in valid, f"{name} tier='{cfg['tier']}'"

    def test_cost_class_values_valid(self):
        valid = {"free", "low", "medium", "high", "variable"}
        presets = load_presets()
        for name, cfg in presets.items():
            assert cfg["cost_class"] in valid, f"{name} cost_class='{cfg['cost_class']}'"


# ─── Model Policy ────────────────────────────────────────────────────


class TestModelPolicy:
    """No prohibited model tiers in presets."""

    def test_no_prohibited_defaults(self):
        import re

        pat = re.compile(
            r"\b(mini|flash|haiku|nano|tiny|small|lite)\b",
            re.IGNORECASE,
        )
        presets = load_presets()
        for name, cfg in presets.items():
            d = cfg.get("default_model", "")
            assert not pat.search(d), f"{name}: '{d}' violates model policy"

    def test_no_prohibited_intent_models(self):
        import re

        pat = re.compile(
            r"\b(mini|flash|haiku|nano|tiny|small|lite)\b",
            re.IGNORECASE,
        )
        presets = load_presets()
        for name, cfg in presets.items():
            for intent, model in cfg.get("intent_model_map", {}).items():
                assert not pat.search(model), f"{name}/{intent}: '{model}' prohibited"


# ─── Query APIs ───────────────────────────────────────────────────────


class TestQueryAPIs:
    """get_providers_by_tier and get_providers_by_cost."""

    def test_frontier_providers(self):
        frontier = get_providers_by_tier("frontier")
        assert "gemini" in frontier
        assert "openai" in frontier
        assert "anthropic" in frontier

    def test_free_providers(self):
        free = get_providers_by_cost("free")
        assert len(free) >= 5

    def test_empty_for_unknown(self):
        assert get_providers_by_tier("nonexistent") == []
        assert get_providers_by_cost("nonexistent") == []


# ─── BaseProvider Defaults ────────────────────────────────────────────


class TestBaseProviderDefaults:
    """BaseProvider has sensible tier/cost defaults."""

    def test_default_tier(self):
        class Dummy(BaseProvider):
            @property
            def provider_name(self):
                return "dummy"

            @property
            def model_name(self):
                return "test"

            async def invoke(self, prompt):
                return "ok"

        assert Dummy().tier == "high"

    def test_default_cost_class(self):
        class Dummy(BaseProvider):
            @property
            def provider_name(self):
                return "dummy"

            @property
            def model_name(self):
                return "test"

            async def invoke(self, prompt):
                return "ok"

        assert Dummy().cost_class == "medium"


# ─── LLMProvider Properties ──────────────────────────────────────────


class TestLLMProviderProperties:
    """LLMProvider reads tier/cost from preset."""

    def test_qwen_tier_and_cost(self):
        from cortex.extensions.llm.provider import LLMProvider

        p = LLMProvider(provider="qwen")
        assert p.tier == "high"
        assert p.cost_class == "low"

    def test_gemini_is_frontier(self):
        os.environ.setdefault("GEMINI_API_KEY", "test")
        from cortex.extensions.llm.provider import LLMProvider

        p = LLMProvider(provider="gemini")
        assert p.tier == "frontier"


# ─── Router Cost-Aware Ordering ──────────────────────────────────────


class TestRouterOrdering:
    """_ordered_fallbacks sorts by cost then tier."""

    @pytest.fixture
    def _providers(self):
        os.environ.setdefault("GEMINI_API_KEY", "test")
        os.environ.setdefault("GROQ_API_KEY", "test")
        os.environ.setdefault("DEEPSEEK_API_KEY", "test")
        from cortex.extensions.llm.provider import LLMProvider

        return {
            "qwen": LLMProvider(provider="qwen"),
            "gemini": LLMProvider(provider="gemini"),
            "groq": LLMProvider(provider="groq"),
            "deepseek": LLMProvider(provider="deepseek"),
        }

    def test_cost_ordering(self, _providers):
        from cortex.extensions.llm.router import CortexLLMRouter

        router = CortexLLMRouter(
            primary=_providers["qwen"],
            fallbacks=[
                _providers["gemini"],
                _providers["groq"],
                _providers["deepseek"],
            ],
        )
        ordered = router._ordered_fallbacks(CortexPrompt(text="test", intent=IntentProfile.CODE))
        costs = [p.cost_class for p in ordered]
        # free < low < medium
        assert costs == ["free", "low", "medium"]

    def test_tier_tiebreaking_within_cost(self, _providers):
        """Same cost → frontier preferred over high."""
        from cortex.extensions.llm.router import CortexLLMRouter

        # deepseek=low/frontier, qwen=low/high
        router = CortexLLMRouter(
            primary=_providers["gemini"],
            fallbacks=[
                _providers["qwen"],
                _providers["deepseek"],
            ],
        )
        ordered = router._ordered_fallbacks(CortexPrompt(text="test", intent=IntentProfile.CODE))
        # Both are "low" cost, but deepseek=frontier, qwen=high
        names = [p.provider_name for p in ordered]
        assert names.index("deepseek") < names.index("qwen")

    def test_cost_order_constants(self):
        from cortex.extensions.llm.router import CortexLLMRouter

        o = CortexLLMRouter._COST_ORDER
        assert o["free"] < o["low"] < o["medium"] < o["high"]

    def test_tier_order_constants(self):
        from cortex.extensions.llm.router import CortexLLMRouter

        t = CortexLLMRouter._TIER_ORDER
        assert t["frontier"] < t["high"] < t["local"]
