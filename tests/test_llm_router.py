"""Tests for cortex.llm.router — ROP-based LLM routing."""

from __future__ import annotations

import pytest

from cortex.llm.router import BaseProvider, CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.utils.result import Err, Ok

# ─── Mock Providers ───────────────────────────────────────────────────


class MockProvider(BaseProvider):
    """Provider that returns a canned response."""

    def __init__(self, name: str, response: str):
        self._name = name
        self._response = response

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-model"

    async def invoke(self, prompt: CortexPrompt) -> str:
        return self._response


class FailingProvider(BaseProvider):
    """Provider that always fails."""

    def __init__(self, name: str, error_msg: str = "connection refused"):
        self._name = name
        self._error_msg = error_msg

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-model"

    async def invoke(self, prompt: CortexPrompt) -> str:
        raise ConnectionError(self._error_msg)


# ─── Tests ────────────────────────────────────────────────────────────


class TestCortexLLMRouter:
    @pytest.fixture
    def prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a helpful assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
        )

    @pytest.mark.asyncio
    async def test_primary_success(self, prompt: CortexPrompt):
        router = CortexLLMRouter(MockProvider("openai", "Hello!"))
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "Hello!"

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, prompt: CortexPrompt):
        router = CortexLLMRouter(
            primary=FailingProvider("openai"),
            fallbacks=[MockProvider("anthropic", "Fallback response")],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "Fallback response"

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_err(self, prompt: CortexPrompt):
        router = CortexLLMRouter(
            primary=FailingProvider("openai", "timeout"),
            fallbacks=[
                FailingProvider("anthropic", "rate limited"),
                FailingProvider("gemini", "quota exceeded"),
            ],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Err)
        assert "All providers failed" in result.error
        assert "openai" in result.error
        assert "anthropic" in result.error
        assert "gemini" in result.error

    @pytest.mark.asyncio
    async def test_no_fallbacks(self, prompt: CortexPrompt):
        router = CortexLLMRouter(primary=FailingProvider("openai"))
        result = await router.invoke(prompt)
        assert isinstance(result, Err)

    @pytest.mark.asyncio
    async def test_execute_resilient_is_same_as_invoke(self, prompt: CortexPrompt):
        router = CortexLLMRouter(MockProvider("openai", "ok"))
        r1 = await router.invoke(prompt)
        r2 = await router.execute_resilient(prompt)
        assert isinstance(r1, Ok)
        assert isinstance(r2, Ok)
        assert r1.value == r2.value


class TestCortexPrompt:
    def test_to_openai_messages_basic(self):
        prompt = CortexPrompt(
            system_instruction="Be helpful",
            working_memory=[{"role": "user", "content": "Hi"}],
        )
        msgs = prompt.to_openai_messages()
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert len(msgs) == 2

    def test_to_openai_messages_with_episodic(self):
        prompt = CortexPrompt(
            system_instruction="Be helpful",
            working_memory=[{"role": "user", "content": "Hi"}],
            episodic_context=[{"role": "memory", "content": "past event"}],
        )
        msgs = prompt.to_openai_messages()
        assert len(msgs) == 3
        assert "episodic_context" in msgs[1]["content"]


# ─── Intent-Aware Cascade Tests ──────────────────────────────────────────────


class CodeSpecialistProvider(BaseProvider):
    """Simulates a code-specialist provider (anthropic, deepseek…)."""

    def __init__(self, name: str, response: str = "code answer"):
        self._name = name
        self._response = response

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-code"

    @property
    def intent_affinity(self) -> frozenset:
        from cortex.llm.router import IntentProfile

        return frozenset({IntentProfile.CODE})

    async def invoke(self, prompt: CortexPrompt) -> str:
        return self._response


class ReasoningSpecialistProvider(BaseProvider):
    """Simulates a reasoning-specialist provider (openai, gemini…)."""

    def __init__(self, name: str, response: str = "reasoning answer"):
        self._name = name
        self._response = response

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-reason"

    @property
    def intent_affinity(self) -> frozenset:
        from cortex.llm.router import IntentProfile

        return frozenset({IntentProfile.REASONING})

    async def invoke(self, prompt: CortexPrompt) -> str:
        return self._response


class TestIntentAwareCascade:
    """Validates that fallbacks are sorted by intent affinity."""

    @pytest.fixture
    def code_prompt(self) -> CortexPrompt:
        from cortex.llm.router import IntentProfile

        return CortexPrompt(
            system_instruction="You are a code assistant.",
            working_memory=[{"role": "user", "content": "Fix the bug"}],
            intent=IntentProfile.CODE,
        )

    @pytest.fixture
    def reasoning_prompt(self) -> CortexPrompt:
        from cortex.llm.router import IntentProfile

        return CortexPrompt(
            system_instruction="You are a reasoning assistant.",
            working_memory=[{"role": "user", "content": "Why did it fail?"}],
            intent=IntentProfile.REASONING,
        )

    @pytest.mark.asyncio
    async def test_code_intent_prefers_code_specialist_fallback(
        self, code_prompt: CortexPrompt
    ):
        """When primary fails with CODE intent, code-specialist fallback wins first."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                ReasoningSpecialistProvider("reasoning-provider"),  # wrong domain
                CodeSpecialistProvider("code-provider", "code fallback used"),  # correct
            ],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Ok)
        # Code specialist must be tried BEFORE the reasoning provider
        assert result.value == "code fallback used"

    @pytest.mark.asyncio
    async def test_reasoning_intent_prefers_reasoning_specialist_fallback(
        self, reasoning_prompt: CortexPrompt
    ):
        """When primary fails with REASONING intent, reasoning-specialist wins."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                CodeSpecialistProvider("code-provider"),  # wrong domain
                ReasoningSpecialistProvider("reasoning-provider", "reasoning fallback used"),
            ],
        )
        result = await router.invoke(reasoning_prompt)
        assert isinstance(result, Ok)
        assert result.value == "reasoning fallback used"

    @pytest.mark.asyncio
    async def test_general_intent_does_not_reorder_fallbacks(
        self, prompt: CortexPrompt
    ):
        """GENERAL intent disables reordering — fallbacks used in registration order."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                MockProvider("first", "first wins"),
                MockProvider("second", "second"),
            ],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "first wins"

    @pytest.mark.asyncio
    async def test_singularidad_negativa_includes_all_providers(
        self, code_prompt: CortexPrompt
    ):
        """Err message lists ALL failed providers regardless of intent."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary", "timeout"),
            fallbacks=[
                FailingProvider("code-fb", "quota"),
                FailingProvider("general-fb", "503"),
            ],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Err)
        assert "primary" in result.error
        assert "code-fb" in result.error
        assert "general-fb" in result.error

    @pytest.fixture
    def prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a helpful assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
        )

# ─── Intent-Typed Mock Providers ──────────────────────────────────────


class TypedMockProvider(MockProvider):
    """Provider with explicit intent_affinity."""

    def __init__(self, name: str, response: str, affinity: frozenset[IntentProfile]):
        super().__init__(name, response)
        self._affinity = affinity

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        return self._affinity


class TypedFailingProvider(FailingProvider):
    """Failing provider with explicit intent_affinity."""

    def __init__(
        self,
        name: str,
        affinity: frozenset[IntentProfile],
        error_msg: str = "connection refused",
    ):
        super().__init__(name, error_msg)
        self._affinity = affinity

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        return self._affinity


# ─── Intent-Aware Routing Tests ───────────────────────────────────────


class TestIntentAwareRouting:
    """Verifica que el cascade es determinista por intención.

    Invariante: el ruido del error nunca cruza dominios de intención
    si existe un fallback con afinidad correcta.
    """

    @pytest.fixture
    def code_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a code expert.",
            working_memory=[{"role": "user", "content": "Fix this bug."}],
            intent=IntentProfile.CODE,
        )

    @pytest.fixture
    def general_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a helpful assistant.",
            working_memory=[{"role": "user", "content": "Hello."}],
            intent=IntentProfile.GENERAL,
        )

    @pytest.mark.asyncio
    async def test_code_prompt_uses_code_typed_fallback_first(
        self, code_prompt: CortexPrompt
    ):
        """CODE prompt selecciona el fallback con afinidad CODE antes que GENERAL."""
        general_fb = TypedMockProvider(
            "general-llm", "generic answer", frozenset({IntentProfile.GENERAL})
        )
        code_fb = TypedMockProvider(
            "deepseek-coder", "precise code answer", frozenset({IntentProfile.CODE})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            # general registrado antes — pero debe ir después en el cascade
            fallbacks=[general_fb, code_fb],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Ok)
        assert result.value == "precise code answer"

    @pytest.mark.asyncio
    async def test_code_prompt_degrades_to_general_as_safety_net(
        self, code_prompt: CortexPrompt
    ):
        """Si todos los fallbacks CODE fallan, el generalista actúa como safety-net."""
        code_fb_failing = TypedFailingProvider(
            "deepseek-coder", frozenset({IntentProfile.CODE}), "rate limited"
        )
        general_fb = TypedMockProvider(
            "gpt-4o", "fallback general answer", frozenset({IntentProfile.GENERAL})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[code_fb_failing, general_fb],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Ok)
        assert result.value == "fallback general answer"

    @pytest.mark.asyncio
    async def test_general_intent_uses_all_fallbacks_in_order(
        self, general_prompt: CortexPrompt
    ):
        """GENERAL intent desactiva el filtro — todos los fallbacks en orden de registro."""
        fb1 = TypedFailingProvider("first", frozenset({IntentProfile.CODE}))
        fb2 = TypedMockProvider(
            "second", "second response", frozenset({IntentProfile.REASONING})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[fb1, fb2],
        )
        result = await router.invoke(general_prompt)
        assert isinstance(result, Ok)
        assert result.value == "second response"

    @pytest.mark.asyncio
    async def test_all_providers_fail_with_intent_returns_err(
        self, code_prompt: CortexPrompt
    ):
        """Singularidad Negativa — error contiene intent en el log, Err bien formado."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary", "timeout"),
            fallbacks=[
                TypedFailingProvider(
                    "deepseek", frozenset({IntentProfile.CODE}), "quota"
                ),
                TypedFailingProvider(
                    "codestral", frozenset({IntentProfile.CODE}), "unavailable"
                ),
            ],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Err)
        assert "All providers failed" in result.error
        assert "primary" in result.error


# ─── Intent Model Map Tests ──────────────────────────────────────────


class TestIntentModelMap:
    """Validates that providers with intent_model_map resolve the correct model per intent."""

    @pytest.fixture(autouse=True)
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def test_openrouter_resolves_code_model(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        resolved = p._resolve_model(IntentProfile.CODE)
        assert "coder" in resolved.lower()

    def test_openrouter_resolves_reasoning_model(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        resolved = p._resolve_model(IntentProfile.REASONING)
        assert "deepseek" in resolved.lower() or "r1" in resolved.lower()

    def test_openrouter_resolves_creative_model(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        resolved = p._resolve_model(IntentProfile.CREATIVE)
        assert "claude" in resolved.lower() or "anthropic" in resolved.lower()

    def test_openrouter_resolves_general_to_default(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        resolved = p._resolve_model(IntentProfile.GENERAL)
        assert resolved == p.model_name  # default_model

    def test_provider_without_map_uses_fixed_model(self, monkeypatch):
        from cortex.llm.provider import LLMProvider

        monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
        p = LLMProvider(provider="cerebras")
        for intent in IntentProfile:
            assert p._resolve_model(intent) == p.model_name

    def test_all_intents_have_eligible_model(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        for intent in IntentProfile:
            resolved = p._resolve_model(intent)
            assert resolved, f"No model resolved for intent {intent.value}"
            assert len(resolved) > 3  # sanity: not empty/garbage
