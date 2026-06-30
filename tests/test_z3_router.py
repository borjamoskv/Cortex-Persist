# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os

os.environ.setdefault("CORTEX_TESTING", "1")

import pytest
from babylon60.extensions.llm._models import BaseProvider, IntentProfile, ReasoningMode, CortexPrompt
from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.config import LLM_LOCAL_FIRST


class MockProvider(BaseProvider):
    def __init__(
        self, name: str, tier: str, cost_class: str, context_window: int, specialization: list[str]
    ) -> None:
        self._name = name
        self._tier = tier
        self._cost_class = cost_class
        self._context_window = context_window
        self._specialization = specialization

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-model"

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_class(self) -> str:
        return self._cost_class

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def intent_affinity(self) -> list[str]:
        return self._specialization

    async def invoke(self, prompt: CortexPrompt) -> str:
        return "response"


@pytest.fixture
def dummy_primary() -> MockProvider:
    return MockProvider("primary", "high", "medium", 128000, ["general"])


def test_z3_requires_frontier_coercion(dummy_primary) -> None:
    # Set up frontier, high and local candidates
    p_frontier = MockProvider("p_frontier", "frontier", "high", 128000, ["reasoning"])
    p_high = MockProvider("p_high", "high", "low", 128000, ["reasoning"])

    router = CortexLLMRouter(primary=dummy_primary, fallbacks=[p_high, p_frontier])

    # 1. Standard prompt without verification terms: p_high (lower cost) preferred first
    prompt_std = CortexPrompt(
        system_instruction="Analyze this layout",
        working_memory=[{"role": "user", "content": "hello"}],
        intent=IntentProfile.REASONING,
        reasoning_mode=None,
        max_tokens=100,
    )
    ordered_std = router._ordered_fallbacks(prompt_std)
    assert [p.provider_name for p in ordered_std] == ["p_high", "p_frontier"]

    # 2. Prompt with verification term "anvil" should coerce to frontier first
    prompt_anvil = CortexPrompt(
        system_instruction="Verify this code using Anvil",
        working_memory=[{"role": "user", "content": "invariant checking"}],
        intent=IntentProfile.REASONING,
        reasoning_mode=None,
        max_tokens=100,
    )
    ordered_anvil = router._ordered_fallbacks(prompt_anvil)
    # p_frontier must be selected first because it has tier == 'frontier'
    assert ordered_anvil[0].provider_name == "p_frontier"


def test_z3_context_window_filtering(dummy_primary) -> None:
    p_small = MockProvider("p_small", "high", "low", 4000, ["code"])
    p_large = MockProvider("p_large", "high", "medium", 128000, ["code"])

    router = CortexLLMRouter(primary=dummy_primary, fallbacks=[p_small, p_large])

    # Create a prompt with large history (total characters ~15000 -> ~5000 tokens)
    large_content = "X" * 15000
    prompt_large = CortexPrompt(
        system_instruction="Solve this",
        working_memory=[{"role": "user", "content": large_content}],
        intent=IntentProfile.CODE,
        reasoning_mode=None,
        max_tokens=2048,
    )

    ordered = router._ordered_fallbacks(prompt_large)
    # p_small (4000 window) should be filtered out by context constraint and placed after p_large
    assert ordered[0].provider_name == "p_large"
    assert ordered[1].provider_name == "p_small"


def test_z3_local_first_ordering(dummy_primary, monkeypatch) -> None:
    # Set up a local provider and a frontier provider
    p_local = MockProvider("p_local", "local", "free", 128000, ["code"])
    p_frontier = MockProvider("p_frontier", "frontier", "medium", 128000, ["code"])

    router = CortexLLMRouter(primary=dummy_primary, fallbacks=[p_local, p_frontier])

    prompt = CortexPrompt(
        system_instruction="Write a function",
        working_memory=[],
        intent=IntentProfile.CODE,
        reasoning_mode=None,
        max_tokens=100,
    )

    # Enable LLM_LOCAL_FIRST
    monkeypatch.setattr("cortex.config.LLM_LOCAL_FIRST", True)
    ordered_local_first = router._ordered_fallbacks(prompt)
    assert ordered_local_first[0].provider_name == "p_local"

    # Disable LLM_LOCAL_FIRST
    monkeypatch.setattr("cortex.config.LLM_LOCAL_FIRST", False)
    ordered_std = router._ordered_fallbacks(prompt)
    # With standard mode, p_local (free) will still be preferred over p_frontier (medium cost) due to cost minimization,
    # let's change p_local to have high cost to test tier preference.
    p_local_expensive = MockProvider("p_local", "local", "high", 128000, ["code"])
    router_expensive = CortexLLMRouter(
        primary=dummy_primary, fallbacks=[p_local_expensive, p_frontier]
    )
    ordered_expensive = router_expensive._ordered_fallbacks(prompt)
    assert ordered_expensive[0].provider_name == "p_frontier"


def test_z3_auto_relaxation(dummy_primary) -> None:
    # If a prompt requires frontier (e.g. ULTRA_THINK) but no candidate is a frontier provider
    p_high = MockProvider("p_high", "high", "low", 128000, ["reasoning"])

    router = CortexLLMRouter(primary=dummy_primary, fallbacks=[p_high])

    prompt = CortexPrompt(
        system_instruction="Verify this constraint",
        working_memory=[],
        intent=IntentProfile.REASONING,
        reasoning_mode=ReasoningMode.ULTRA_THINK,
        max_tokens=100,
    )

    # Should not fail. Constraint relaxation should kick in and return the available high-tier provider.
    ordered = router._ordered_fallbacks(prompt)
    assert len(ordered) == 1
    assert ordered[0].provider_name == "p_high"
