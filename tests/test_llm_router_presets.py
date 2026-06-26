# [C5-REAL] Exergy-Maximized
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

from cortex_extensions.llm._models import BaseProvider, IntentProfile
from cortex_extensions.llm._presets import (
    _PRESETS_CACHE,
    frontier_providers,
    load_presets,
    providers_for_intent,
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
            if "heretic" in d.lower():
                continue
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
                if "heretic" in model.lower():
                    continue
                assert not pat.search(model), f"{name}/{intent}: '{model}' prohibited"


# ─── Query APIs ───────────────────────────────────────────────────────


class TestQueryAPIs:
    """providers_for_intent and helpers."""

    def test_frontier_providers(self):
        frontier = [p[0] for p in frontier_providers("general")]
        assert "gemini" in frontier
        assert "openai" in frontier
        assert "anthropic" in frontier

    def test_free_providers(self):
        # max_cost="free" ensures we get only free cost class
        free = [p[0] for p in providers_for_intent("general", min_tier="local", max_cost="free")]
        assert len(free) >= 5

    def test_empty_for_unknown(self):
        assert (
            providers_for_intent("nonexistent_intent", min_tier="frontier", max_cost="free") == []
        )


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
        from cortex_extensions.llm.provider import LLMProvider

        p = LLMProvider(provider="qwen")
        assert p.tier == "frontier"
        assert p.cost_class == "low"

    def test_gemini_is_frontier(self):
        os.environ.setdefault("GEMINI_API_KEY", "test")
        from cortex_extensions.llm.provider import LLMProvider

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
        from cortex_extensions.llm.provider import LLMProvider

        return {
            "qwen": LLMProvider(provider="qwen"),
            "gemini": LLMProvider(provider="gemini"),
            "groq": LLMProvider(provider="groq"),
            "deepseek": LLMProvider(provider="deepseek"),
        }

    def test_cost_ordering(self, _providers):
        from cortex_extensions.llm.router import CortexLLMRouter

        router = CortexLLMRouter(
            primary=_providers["qwen"],
            fallbacks=[
                _providers["gemini"],
                _providers["groq"],
                _providers["deepseek"],
            ],
        )

        class MockPrompt:
            intent = IntentProfile.CODE
            reasoning_mode = "standard"

        ordered = router._ordered_fallbacks(MockPrompt())
        costs = [p.cost_class for p in ordered]
        # free < low < medium
        assert costs == ["free", "low", "medium"]

    def test_tier_tiebreaking_within_cost(self, _providers):
        """Same cost → frontier preferred over high."""
        from cortex_extensions.llm.router import CortexLLMRouter

        p1 = _providers["groq"]
        p2 = _providers["deepseek"]
        # Force same cost but different tiers, and same capabilities to ensure they sort together
        p1._tier = "high"
        p1._cost_class = "low"
        p1._capabilities = ["code", "chat"]
        p2._tier = "frontier"
        p2._cost_class = "low"
        p2._capabilities = ["code", "chat"]

        router = CortexLLMRouter(
            primary=_providers["gemini"],
            fallbacks=[p1, p2],
        )

        class MockPrompt:
            intent = IntentProfile.CODE
            reasoning_mode = "standard"

        ordered = router._ordered_fallbacks(MockPrompt())
        # Both may be "low" cost, but deepseek is frontier
        names = [p.provider_name for p in ordered]
        assert names.index("deepseek") < names.index("groq")

    def test_cost_order_constants(self):
        from cortex_extensions.llm._router_policy import COST_ORDER

        o = COST_ORDER
        assert isinstance(o, dict)
        assert "free" in o

    def test_tier_order_constants(self):
        from cortex_extensions.llm._router_policy import TIER_ORDER

        t = TIER_ORDER
        assert t["frontier"] < t["high"] < t["local"]


class TestAPIKeyFallbacks:
    """Verifies check_api_key resolves fallback env vars correctly."""

    def test_fallback_moonshot_to_kimi(self, monkeypatch):
        from cortex_extensions.llm._presets import check_api_key

        monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
        monkeypatch.setenv("KIMI_API_KEY", "kimi-secret-token")

        preset = {"env_key": "MOONSHOT_API_KEY"}
        assert check_api_key(preset) == "kimi-secret-token"

    def test_fallback_xai_to_grok(self, monkeypatch):
        from cortex_extensions.llm._presets import check_api_key

        monkeypatch.delenv("XAI_API_KEY", raising=False)
        monkeypatch.setenv("GROK_API_KEY", "grok-secret-token")

        preset = {"env_key": "XAI_API_KEY"}
        assert check_api_key(preset) == "grok-secret-token"

    def test_fallback_grok_to_xai(self, monkeypatch):
        from cortex_extensions.llm._presets import check_api_key

        monkeypatch.delenv("GROK_API_KEY", raising=False)
        monkeypatch.setenv("XAI_API_KEY", "xai-secret-token")

        preset = {"env_key": "GROK_API_KEY"}
        assert check_api_key(preset) == "xai-secret-token"

    def test_grok_preset_uses_env_key(self):
        from cortex_extensions.llm._presets import load_presets

        presets = load_presets()
        grok_preset = presets.get("grok", {})
        assert grok_preset.get("env_key") == "GROK_API_KEY"
        assert "api_key" not in grok_preset
