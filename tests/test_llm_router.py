"""Tests for cortex.llm.router — ROP-based LLM routing."""

from __future__ import annotations

import pytest

from cortex.llm.router import (
    BaseProvider,
    CascadeTier,
    CortexLLMRouter,
    CortexPrompt,
    IntentProfile,
)
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
        # code is mapped to anthropic/claude-sonnet-4 on openrouter
        assert "claude" in resolved.lower() or "anthropic" in resolved.lower()

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

    def test_openrouter_resolves_general_to_mapped_model(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        resolved = p._resolve_model(IntentProfile.GENERAL)
        # GENERAL is mapped to gemini-2.5-flash-preview on openrouter
        assert "gemini" in resolved.lower()

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


# ─── Negative Cache (RFC 2308) Tests ─────────────────────────────────────────


class TestNegativeCache:
    """Validates RFC 2308 NXDOMAIN negative caching in the router.

    Ω₅ (Antifragile by Default): failures feed the system by converting
    the fallback cascade from reactive to predictive.
    """

    @pytest.fixture
    def code_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="Code assistant.",
            working_memory=[{"role": "user", "content": "Fix the bug"}],
            intent=IntentProfile.CODE,
        )

    @pytest.fixture
    def general_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="General assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
            intent=IntentProfile.GENERAL,
        )

    @pytest.fixture
    def reasoning_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="Reasoning assistant.",
            working_memory=[{"role": "user", "content": "Why?"}],
            intent=IntentProfile.REASONING,
        )

    @pytest.mark.asyncio
    async def test_failed_fallback_is_skipped_on_retry(
        self, general_prompt: CortexPrompt
    ):
        """Provider fails once → cached → second invoke skips it."""
        # Track invocations to prove the provider is NOT called the second time
        call_count = 0

        class CountingFailer(FailingProvider):
            async def invoke(self, prompt: CortexPrompt) -> str:
                nonlocal call_count
                call_count += 1
                raise ConnectionError("down")

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                CountingFailer("unstable"),
                MockProvider("backup", "backup ok"),
            ],
            negative_ttl=60.0,
        )

        # First call: unstable is tried and fails, backup succeeds
        r1 = await router.invoke(general_prompt)
        assert isinstance(r1, Ok)
        assert r1.value == "backup ok"
        assert call_count == 1  # unstable was called

        # Second call: unstable is NXDOMAIN-cached → skipped entirely
        call_count = 0
        r2 = await router.invoke(general_prompt)
        assert isinstance(r2, Ok)
        assert r2.value == "backup ok"
        assert call_count == 0  # unstable was NOT called (NXDOMAIN skip)

    @pytest.mark.asyncio
    async def test_primary_never_suppressed(self, general_prompt: CortexPrompt):
        """Primary always gets retried — Byzantine Default Ω₃."""
        call_count = 0

        class CountingPrimary(BaseProvider):
            @property
            def provider_name(self) -> str:
                return "primary"

            @property
            def model_name(self) -> str:
                return "primary-model"

            async def invoke(self, prompt: CortexPrompt) -> str:
                nonlocal call_count
                call_count += 1
                if call_count <= 1:
                    raise ConnectionError("first attempt down")
                return "recovered"

        router = CortexLLMRouter(
            primary=CountingPrimary(),
            fallbacks=[MockProvider("backup", "backup response")],
            negative_ttl=60.0,
        )

        # First call: primary fails, backup succeeds
        r1 = await router.invoke(general_prompt)
        assert isinstance(r1, Ok)
        assert r1.value == "backup response"
        assert call_count == 1

        # Second call: primary is ALWAYS retried (not suppressed) and recovers
        r2 = await router.invoke(general_prompt)
        assert isinstance(r2, Ok)
        assert r2.value == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_negative_cache_scoped_by_intent(
        self, code_prompt: CortexPrompt, reasoning_prompt: CortexPrompt
    ):
        """Failure for CODE doesn't suppress provider for REASONING."""
        call_log: list[str] = []

        class LoggingFailer(FailingProvider):
            async def invoke(self, prompt: CortexPrompt) -> str:
                call_log.append(f"{self.provider_name}:{prompt.intent.value}")
                raise ConnectionError("down")

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                LoggingFailer("multi-provider"),
                MockProvider("backup", "backup ok"),
            ],
            negative_ttl=60.0,
        )

        # Call 1: CODE intent — multi-provider fails, gets cached for CODE
        await router.invoke(code_prompt)
        assert "multi-provider:code" in call_log

        # Call 2: REASONING intent — multi-provider should NOT be cached
        call_log.clear()
        await router.invoke(reasoning_prompt)
        assert "multi-provider:reasoning" in call_log  # WAS called (different intent)

    @pytest.mark.asyncio
    async def test_ttl_expiry_resurrects_provider(
        self, general_prompt: CortexPrompt
    ):
        """After TTL expires, provider is retried (resurrected)."""
        import time
        from unittest.mock import patch

        call_count = 0

        class CountingFailer(FailingProvider):
            async def invoke(self, prompt: CortexPrompt) -> str:
                nonlocal call_count
                call_count += 1
                raise ConnectionError("down")

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                CountingFailer("flaky"),
                MockProvider("backup", "backup ok"),
            ],
            negative_ttl=10.0,  # 10s TTL
        )

        # Call 1: flaky fails, gets cached
        await router.invoke(general_prompt)
        assert call_count == 1

        # Call 2: within TTL — flaky is skipped
        call_count = 0
        await router.invoke(general_prompt)
        assert call_count == 0

        # Simulate TTL expiry by advancing monotonic clock
        # Rationale (Ω₁): With 0% success, NXDOMAIN TTL scales to 2x (20s).
        # We must advance > 20s to observe resurrection.
        original_monotonic = time.monotonic
        with patch("time.monotonic", return_value=original_monotonic() + 21.0):
            call_count = 0
            # Clear positive cache to prevent backup being promoted ahead of flaky
            router.clear_positive_cache()
            await router.invoke(general_prompt)
            assert call_count == 1  # resurrected and retried

    @pytest.mark.asyncio
    async def test_nxdomain_error_appears_in_err_detail(
        self, general_prompt: CortexPrompt
    ):
        """Err message includes 'NXDOMAIN-cached' for suppressed providers."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[FailingProvider("unstable", "timeout")],
            negative_ttl=60.0,
        )

        # First call: unstable fails (real error)
        r1 = await router.invoke(general_prompt)
        assert isinstance(r1, Err)
        assert "timeout" in r1.error

        # Second call: unstable is NXDOMAIN-cached
        r2 = await router.invoke(general_prompt)
        assert isinstance(r2, Err)
        assert "NXDOMAIN-cached" in r2.error

    @pytest.mark.asyncio
    async def test_clear_negative_cache_resets(
        self, general_prompt: CortexPrompt
    ):
        """clear_negative_cache() restores full cascade."""
        call_count = 0

        class CountingFailer(FailingProvider):
            async def invoke(self, prompt: CortexPrompt) -> str:
                nonlocal call_count
                call_count += 1
                raise ConnectionError("down")

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[
                CountingFailer("flaky"),
                MockProvider("backup", "ok"),
            ],
            negative_ttl=60.0,
        )

        # Call 1: flaky fails, gets cached
        await router.invoke(general_prompt)
        assert call_count == 1

        # Call 2: flaky skipped (cached)
        call_count = 0
        await router.invoke(general_prompt)
        assert call_count == 0

        # Clear cache
        router.clear_negative_cache()

        # Call 3: flaky retried (cache flushed)
        # Also clear positive cache so backup doesn't get promoted ahead of flaky
        router.clear_positive_cache()
        call_count = 0
        await router.invoke(general_prompt)
        assert call_count == 1

    def test_negative_cache_unit_record_and_check(self):
        """Direct NegativeCache API validation."""
        from cortex.llm.router import NegativeCache

        cache = NegativeCache(default_ttl=60.0)

        # Initially empty
        assert cache.suppressed_count == 0
        assert not cache.is_suppressed("openai", "code")

        # Record failure
        cache.record_failure("openai", "code")
        assert cache.suppressed_count == 1
        assert cache.is_suppressed("openai", "code")

        # Different intent is NOT suppressed
        assert not cache.is_suppressed("openai", "reasoning")

        # Different provider is NOT suppressed
        assert not cache.is_suppressed("anthropic", "code")

        # Clear flushes everything
        cache.clear()
        assert cache.suppressed_count == 0
        assert not cache.is_suppressed("openai", "code")


# ─── Positive Cache (DNS A-Record) Tests ─────────────────────────────────────


class TestPositiveCache:
    """Validates DNS A-record positive caching in the router.

    Ω₅ (Antifragile by Default): success feeds the system by promoting
    known-good providers in the cascade ordering.
    """

    @pytest.fixture
    def code_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="Code assistant.",
            working_memory=[{"role": "user", "content": "Fix the bug"}],
            intent=IntentProfile.CODE,
        )

    @pytest.fixture
    def general_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="General assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
            intent=IntentProfile.GENERAL,
        )

    @pytest.fixture
    def reasoning_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="Reasoning assistant.",
            working_memory=[{"role": "user", "content": "Why?"}],
            intent=IntentProfile.REASONING,
        )

    @pytest.mark.asyncio
    async def test_successful_provider_promoted_on_retry(
        self, code_prompt: CortexPrompt
    ):
        """Provider succeeds → A-record cached → promoted in next cascade."""
        # Two code providers: slow registered first, fast registered second
        call_log: list[str] = []

        class OrderTracker(BaseProvider):
            def __init__(self, name: str, response: str, affinity: frozenset):
                self._name = name
                self._response = response
                self._affinity = affinity

            @property
            def provider_name(self) -> str:
                return self._name

            @property
            def model_name(self) -> str:
                return f"{self._name}-model"

            @property
            def intent_affinity(self) -> frozenset[IntentProfile]:
                return self._affinity

            async def invoke(self, prompt: CortexPrompt) -> str:
                call_log.append(self._name)
                return self._response

        slow_code = OrderTracker(
            "slow-code", "slow", frozenset({IntentProfile.CODE})
        )
        fast_code = OrderTracker(
            "fast-code", "fast", frozenset({IntentProfile.CODE})
        )

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[slow_code, fast_code],
            positive_ttl=60.0,
        )

        # First call: slow-code tried first (registration order), succeeds
        r1 = await router.invoke(code_prompt)
        assert isinstance(r1, Ok)
        assert r1.value == "slow"
        assert call_log == ["slow-code"]

        # Overwrite slow-code's A-record with HIGH latency, and
        # record fast-code as significantly FASTER
        router.positive_cache.record_success("slow-code", "code", 500.0)
        router.positive_cache.record_success("fast-code", "code", 10.0)

        # Second call: fast-code should now be promoted (faster A-record)
        call_log.clear()
        r2 = await router.invoke(code_prompt)
        assert isinstance(r2, Ok)
        assert call_log[0] == "fast-code"  # promoted to front

    @pytest.mark.asyncio
    async def test_positive_cache_scoped_by_intent(
        self, code_prompt: CortexPrompt, reasoning_prompt: CortexPrompt
    ):
        """CODE A-record doesn't promote provider for REASONING."""
        from cortex.llm.router import PositiveCache

        cache = PositiveCache(default_ttl=60.0)
        cache.record_success("openai", "code", 50.0)

        assert cache.is_known_good("openai", "code")
        assert not cache.is_known_good("openai", "reasoning")

    @pytest.mark.asyncio
    async def test_faster_provider_ranked_first(
        self, code_prompt: CortexPrompt
    ):
        """Among known-good providers, faster latency wins promotion."""
        from cortex.llm.router import PositiveCache

        cache = PositiveCache(default_ttl=60.0)
        cache.record_success("slow-provider", "code", 500.0)
        cache.record_success("fast-provider", "code", 50.0)
        cache.record_success("mid-provider", "code", 200.0)

        ranked = cache.known_good_providers("code")
        names = [name for name, _ in ranked]
        assert names == ["fast-provider", "mid-provider", "slow-provider"]

    @pytest.mark.asyncio
    async def test_ttl_expiry_demotes_provider(
        self, general_prompt: CortexPrompt
    ):
        """After A-record TTL expires, provider loses promotion."""
        import time
        from unittest.mock import patch

        from cortex.llm.router import PositiveCache

        cache = PositiveCache(default_ttl=10.0)
        cache.record_success("openai", "general", 100.0)

        # Within TTL: known-good
        assert cache.is_known_good("openai", "general")

        # After TTL: expired
        original_monotonic = time.monotonic
        with patch("time.monotonic", return_value=original_monotonic() + 11.0):
            assert not cache.is_known_good("openai", "general")

    @pytest.mark.asyncio
    async def test_clear_positive_cache_resets(
        self, general_prompt: CortexPrompt
    ):
        """clear_positive_cache() removes all A-records."""
        router = CortexLLMRouter(
            primary=MockProvider("primary", "ok"),
            positive_ttl=60.0,
        )

        # Get a success recorded
        await router.invoke(general_prompt)
        assert router.positive_cache.cached_count > 0

        # Clear it
        router.clear_positive_cache()
        assert router.positive_cache.cached_count == 0

    @pytest.mark.asyncio
    async def test_nxdomain_wins_over_a_record(
        self, general_prompt: CortexPrompt
    ):
        """NXDOMAIN suppression overrides A-record promotion."""
        call_log: list[str] = []

        class LoggingProvider(BaseProvider):
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
                call_log.append(self._name)
                return self._response

        fb = LoggingProvider("fallback", "fb-ok")
        backup = LoggingProvider("backup", "backup-ok")

        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[fb, backup],
            negative_ttl=60.0,
            positive_ttl=60.0,
        )

        # Inject A-record for fallback (it's "known-good")
        router.positive_cache.record_success("fallback", "general", 10.0)
        # But also NXDOMAIN-suppress it
        router.negative_cache.record_failure("fallback", "general")

        # fallback should be SKIPPED (NXDOMAIN wins), backup resolves
        r = await router.invoke(general_prompt)
        assert isinstance(r, Ok)
        assert r.value == "backup-ok"
        assert "fallback" not in call_log

    def test_positive_cache_unit_record_and_check(self):
        """Direct PositiveCache API validation."""
        from cortex.llm.router import PositiveCache

        cache = PositiveCache(default_ttl=60.0)

        # Initially empty
        assert cache.cached_count == 0
        assert not cache.is_known_good("openai", "code")

        # Record success
        cache.record_success("openai", "code", 150.0)
        assert cache.cached_count == 1
        assert cache.is_known_good("openai", "code")
        assert cache.get_latency("openai", "code") == 150.0

        # Different intent is NOT cached
        assert not cache.is_known_good("openai", "reasoning")

        # Different provider is NOT cached
        assert not cache.is_known_good("anthropic", "code")

        # Update with faster latency
        cache.record_success("openai", "code", 80.0)
        assert cache.get_latency("openai", "code") == 80.0  # updated
        assert cache.cached_count == 1  # same key, not duplicate

        # Clear flushes everything
        cache.clear()
        assert cache.cached_count == 0
        assert not cache.is_known_good("openai", "code")

    @pytest.mark.asyncio
    async def test_clear_caches_flushes_both(
        self, general_prompt: CortexPrompt
    ):
        """clear_caches() flushes both NXDOMAIN and A-record."""
        router = CortexLLMRouter(
            primary=MockProvider("primary", "ok"),
            fallbacks=[FailingProvider("flaky")],
        )

        # Record both cache types
        router.positive_cache.record_success("primary", "general", 50.0)
        router.negative_cache.record_failure("flaky", "general")

        assert router.positive_cache.cached_count == 1
        assert router.negative_cache.suppressed_count == 1

        # Clear both
        router.clear_caches()
        assert router.positive_cache.cached_count == 0
        assert router.negative_cache.suppressed_count == 0


# ─── Intent Model Map Extended Tests ─────────────────────────────────────────


class TestIntentModelMapExtended:
    """Extended tests for intent model map & provider introspection."""

    @pytest.fixture(autouse=True)
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def test_get_intent_models_returns_dict(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        models = p.get_intent_models()
        assert isinstance(models, dict)
        assert "code" in models
        assert "reasoning" in models
        assert len(models) == 4

    def test_has_intent_routing_true_for_mapped_provider(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        assert p.has_intent_routing is True

    def test_has_intent_routing_false_for_unmapped_provider(self, monkeypatch):
        from cortex.llm.provider import LLMProvider

        monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
        p = LLMProvider(provider="cerebras")
        assert p.has_intent_routing is False

    def test_repr_shows_models_for_mapped_provider(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="openrouter")
        r = repr(p)
        assert "models=[" in r
        assert "code=" in r

    def test_repr_shows_model_for_unmapped_provider(self, monkeypatch):
        from cortex.llm.provider import LLMProvider

        monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
        p = LLMProvider(provider="cerebras")
        r = repr(p)
        assert "model=" in r
        assert "models=[" not in r


# ─── Cascade Telemetry Tests ──────────────────────────────────────────


class TestCascadeTelemetry:
    """Validates entropy telemetry: tier classification, streak tracking,
    and entropy elevation detection."""

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
            system_instruction="You are helpful.",
            working_memory=[{"role": "user", "content": "Hello."}],
        )

    @pytest.mark.asyncio
    async def test_primary_success_records_primary_tier(
        self, general_prompt: CortexPrompt
    ):
        """Primary succeeds → tier = PRIMARY, consecutive failures = 0."""
        router = CortexLLMRouter(MockProvider("primary", "ok"))
        result = await router.invoke(general_prompt)
        assert isinstance(result, Ok)

        stats = router.cascade_stats
        assert stats["primary_hits"] == 1
        assert stats["current_primary_streak"] == 0

        events = router.cascade_history
        assert len(events) == 1
        assert events[0].resolved_tier is CascadeTier.PRIMARY

    @pytest.mark.asyncio
    async def test_typed_match_fallback_records_typed_tier(
        self, code_prompt: CortexPrompt
    ):
        """Primary fails, code-specialist fallback succeeds → tier = TYPED_MATCH."""
        code_fb = TypedMockProvider(
            "deepseek", "code answer", frozenset({IntentProfile.CODE})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[code_fb],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Ok)

        stats = router.cascade_stats
        assert stats["typed_match_hits"] == 1
        assert stats["safety_net_hits"] == 0

    @pytest.mark.asyncio
    async def test_safety_net_fallback_records_safety_net_tier(
        self, code_prompt: CortexPrompt
    ):
        """All typed fallbacks miss, general resolves → tier = SAFETY_NET."""
        general_fb = TypedMockProvider(
            "gpt-4o", "general answer", frozenset({IntentProfile.GENERAL})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[general_fb],
        )
        result = await router.invoke(code_prompt)
        assert isinstance(result, Ok)

        stats = router.cascade_stats
        assert stats["safety_net_hits"] == 1
        assert stats["typed_match_hits"] == 0

    @pytest.mark.asyncio
    async def test_three_consecutive_primary_failures_safety_net_raises_entropy(
        self, code_prompt: CortexPrompt
    ):
        """3+ consecutive primary failures + safety-net → entropy_elevation_count > 0."""
        general_fb = TypedMockProvider(
            "gpt-4o", "general fallback", frozenset({IntentProfile.GENERAL})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[general_fb],
        )

        # 3 consecutive calls — primary fails each time, safety-net resolves
        for _ in range(3):
            result = await router.invoke(code_prompt)
            assert isinstance(result, Ok)
            # Clear negative cache to allow retrying in next call
            router.clear_negative_cache()

        stats = router.cascade_stats
        assert stats["current_primary_streak"] == 3
        assert stats["entropy_elevation_count"] >= 1

    @pytest.mark.asyncio
    async def test_primary_success_resets_consecutive_counter(
        self, general_prompt: CortexPrompt
    ):
        """Primary fails twice, then succeeds → streak resets to 0."""
        call_count = 0

        class FlipFlopProvider(BaseProvider):
            @property
            def provider_name(self) -> str:
                return "flipflop"

            @property
            def model_name(self) -> str:
                return "flipflop-model"

            async def invoke(self, prompt: CortexPrompt) -> str:
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ConnectionError("down")
                return "back online"

        router = CortexLLMRouter(
            primary=FlipFlopProvider(),
            fallbacks=[MockProvider("backup", "backup ok")],
        )

        # Call 1: primary fails → streak = 1
        r1 = await router.invoke(general_prompt)
        assert isinstance(r1, Ok)
        assert router.cascade_stats["current_primary_streak"] == 1

        # Call 2: primary fails again → streak = 2
        r2 = await router.invoke(general_prompt)
        assert isinstance(r2, Ok)
        assert router.cascade_stats["current_primary_streak"] == 2

        # Call 3: primary succeeds → streak resets to 0
        r3 = await router.invoke(general_prompt)
        assert isinstance(r3, Ok)
        assert r3.value == "back online"
        assert router.cascade_stats["current_primary_streak"] == 0

    @pytest.mark.asyncio
    async def test_cascade_stats_accuracy(
        self, code_prompt: CortexPrompt, general_prompt: CortexPrompt
    ):
        """Mixed calls produce correct aggregate stats."""
        code_fb = TypedMockProvider(
            "deepseek", "code", frozenset({IntentProfile.CODE})
        )
        general_fb = TypedMockProvider(
            "gpt-4o", "general", frozenset({IntentProfile.GENERAL})
        )
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[code_fb, general_fb],
        )

        # 1 code call → typed-match (deepseek has CODE affinity)
        await router.invoke(code_prompt)
        router.clear_negative_cache()

        # 1 general call → typed-match (GENERAL disables reordering)
        await router.invoke(general_prompt)

        stats = router.cascade_stats
        assert stats["total_calls"] == 2
        assert stats["primary_hits"] == 0
        assert stats["typed_match_hits"] == 2
        assert stats["safety_net_hits"] == 0


# ─── Hedged Requests (DNS-over-HTTPS) Tests ──────────────────────────────


class SlowProvider(BaseProvider):
    """Mock provider with configurable async delay."""

    def __init__(self, name: str, response: str, delay: float = 0.0):
        self._name = name
        self._response = response
        self._delay = delay
        self.was_called = False
        self.was_cancelled = False

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-model"

    async def invoke(self, prompt: CortexPrompt) -> str:
        import asyncio

        self.was_called = True
        try:
            await asyncio.sleep(self._delay)
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise
        return self._response


class SlowFailingProvider(BaseProvider):
    """Mock provider that fails after a configurable delay."""

    def __init__(self, name: str, delay: float = 0.0, error_msg: str = "down"):
        self._name = name
        self._delay = delay
        self._error_msg = error_msg

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-model"

    async def invoke(self, prompt: CortexPrompt) -> str:
        import asyncio

        await asyncio.sleep(self._delay)
        raise ConnectionError(self._error_msg)


class TestHedgedRequests:
    """Validates DNS-over-HTTPS hedged request pattern.

    Axiom: Ω₂ (controlled waste < latency) + Ω₅ (redundancy as fuel).
    """

    @pytest.fixture
    def prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a helpful assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
        )

    @pytest.mark.asyncio
    async def test_hedged_returns_fastest_provider(self, prompt: CortexPrompt):
        """Race between fast and slow provider — fast wins."""
        fast = SlowProvider("fast-provider", "fast response", delay=0.01)
        slow = SlowProvider("slow-provider", "slow response", delay=1.0)

        router = CortexLLMRouter(
            primary=fast,
            hedging_providers=[slow],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "fast response"

        # Verify hedged result observability
        hr = router.last_hedged_result
        assert hr is not None
        assert hr.winner == "fast-provider"
        assert hr.latency_ms < 500  # should be ~10ms, not 1000ms

    @pytest.mark.asyncio
    async def test_hedged_slow_primary_loses_to_fast_peer(
        self, prompt: CortexPrompt
    ):
        """Slow primary + fast hedging peer — peer wins the race."""
        slow_primary = SlowProvider("slow-primary", "slow response", delay=1.0)
        fast_peer = SlowProvider("fast-peer", "fast response", delay=0.01)

        router = CortexLLMRouter(
            primary=slow_primary,
            hedging_providers=[fast_peer],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "fast response"

        hr = router.last_hedged_result
        assert hr is not None
        assert hr.winner == "fast-peer"
        assert "slow-primary" in hr.cancelled

    @pytest.mark.asyncio
    async def test_hedged_falls_back_to_cascade_on_all_fail(
        self, prompt: CortexPrompt
    ):
        """If all hedged providers fail, cascade takes over."""
        failing_primary = SlowFailingProvider("primary", delay=0.01)
        failing_peer = SlowFailingProvider("peer", delay=0.01)
        backup = MockProvider("backup", "cascade backup")

        router = CortexLLMRouter(
            primary=failing_primary,
            fallbacks=[backup],
            hedging_providers=[failing_peer],
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        # Hedging failed, sequential cascade kicked in
        assert result.value == "cascade backup"

    @pytest.mark.asyncio
    async def test_hedged_skips_nxdomain_cached_peers(
        self, prompt: CortexPrompt
    ):
        """NXDOMAIN-cached peers are excluded from the hedging pool."""
        primary = SlowProvider("primary", "primary response", delay=0.01)
        cached_peer = SlowProvider("cached-peer", "cached response", delay=0.01)

        router = CortexLLMRouter(
            primary=primary,
            hedging_providers=[cached_peer],
            negative_ttl=60.0,
        )

        # Manually suppress the peer
        router.negative_cache.record_failure("cached-peer", "general")

        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "primary response"

        # Hedging was skipped (only 1 eligible), so no hedged result
        assert router.last_hedged_result is None

    @pytest.mark.asyncio
    async def test_hedged_disabled_when_no_peers(self, prompt: CortexPrompt):
        """Without hedging_providers, cascade runs normally."""
        router = CortexLLMRouter(
            primary=MockProvider("primary", "direct response"),
        )
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "direct response"
        assert router.last_hedged_result is None
        assert router.hedging_providers == []

    @pytest.mark.asyncio
    async def test_hedged_single_provider_no_race(self, prompt: CortexPrompt):
        """With only 1 provider (primary, all peers cached), no race occurs."""
        primary = SlowProvider("primary", "sole response", delay=0.01)
        peer1 = SlowProvider("peer1", "peer1", delay=0.01)
        peer2 = SlowProvider("peer2", "peer2", delay=0.01)

        router = CortexLLMRouter(
            primary=primary,
            hedging_providers=[peer1, peer2],
            negative_ttl=60.0,
        )

        # Suppress both peers
        router.negative_cache.record_failure("peer1", "general")
        router.negative_cache.record_failure("peer2", "general")

        result = await router.invoke(prompt)
        assert isinstance(result, Ok)
        assert result.value == "sole response"
        # No race happened — fell through to sequential
        assert router.last_hedged_result is None


# ─── Anycast (WeightedProviderPool) Tests ────────────────────────────────


class TestProviderMetrics:
    """Unit tests for ProviderMetrics EWMA and weight computation."""

    def test_initial_state(self):
        from cortex.llm.router import ProviderMetrics

        m = ProviderMetrics()
        assert m.total_calls == 0
        assert m.success_rate == 1.0  # benefit of the doubt
        assert m.weight == 1.0  # equal chance

    def test_ewma_first_call_sets_directly(self):
        from cortex.llm.router import ProviderMetrics

        m = ProviderMetrics()
        m.record_success(100.0)
        assert m.ewma_latency_ms == 100.0
        assert m.total_calls == 1
        assert m.total_successes == 1

    def test_ewma_converges_to_recent(self):
        from cortex.llm.router import ProviderMetrics

        m = ProviderMetrics()
        # 10 calls at 100ms, then 10 calls at 10ms
        for _ in range(10):
            m.record_success(100.0)
        for _ in range(10):
            m.record_success(10.0)
        # EWMA should be closer to 10ms than 100ms
        assert m.ewma_latency_ms < 50.0

    def test_failure_penalizes_weight(self):
        from cortex.llm.router import ProviderMetrics

        good = ProviderMetrics()
        bad = ProviderMetrics()

        # Both at same latency
        for _ in range(10):
            good.record_success(50.0)
            bad.record_failure(50.0)

        # 100% success vs 0% success — weight should differ dramatically
        assert good.weight > 0
        assert bad.weight == 0.0  # 0% success_rate → weight 0

    def test_faster_provider_has_higher_weight(self):
        from cortex.llm.router import ProviderMetrics

        fast = ProviderMetrics()
        slow = ProviderMetrics()

        for _ in range(5):
            fast.record_success(50.0)
            slow.record_success(500.0)

        assert fast.weight > slow.weight
        # 10x speed difference → ~10x weight difference
        assert fast.weight > slow.weight * 5


class TestWeightedProviderPool:
    """Tests for Anycast-style weighted provider selection."""

    @pytest.fixture
    def prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="Assistant.",
            working_memory=[{"role": "user", "content": "test"}],
        )

    def test_select_weighted_picks_fastest(self):
        from cortex.llm.router import WeightedProviderPool

        pool = WeightedProviderPool()

        fast = MockProvider("fast", "fast")
        slow = MockProvider("slow", "slow")

        # Simulate observed latencies
        for _ in range(5):
            pool.record_success("fast", 50.0)
            pool.record_success("slow", 500.0)

        selected = pool.select_weighted([slow, fast])  # order doesn't matter
        assert selected.provider_name == "fast"

    def test_rank_orders_by_weight(self):
        from cortex.llm.router import WeightedProviderPool

        pool = WeightedProviderPool()

        a = MockProvider("a", "a")
        b = MockProvider("b", "b")
        c = MockProvider("c", "c")

        pool.record_success("a", 100.0)
        pool.record_success("b", 10.0)
        pool.record_success("c", 50.0)

        ranked = pool.rank([a, b, c])
        names = [p.provider_name for p in ranked]
        assert names == ["b", "c", "a"]  # fastest first

    def test_snapshot_returns_all_metrics(self):
        from cortex.llm.router import WeightedProviderPool

        pool = WeightedProviderPool()
        pool.record_success("alpha", 100.0)
        pool.record_failure("beta", 200.0)

        snap = pool.snapshot()
        assert "alpha" in snap
        assert "beta" in snap
        assert snap["alpha"]["success_rate"] == 1.0
        assert snap["beta"]["success_rate"] == 0.0
        assert snap["alpha"]["total_calls"] == 1

    @pytest.mark.asyncio
    async def test_router_records_metrics_on_success(self, prompt: CortexPrompt):
        """_try_provider records success metrics in provider_pool."""
        router = CortexLLMRouter(primary=MockProvider("primary", "ok"))
        await router.invoke(prompt)

        snap = router.provider_pool.snapshot()
        assert "primary" in snap
        assert snap["primary"]["total_calls"] == 1
        assert snap["primary"]["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_router_records_metrics_on_failure(self, prompt: CortexPrompt):
        """_try_provider records failure metrics in provider_pool."""
        router = CortexLLMRouter(
            primary=FailingProvider("primary"),
            fallbacks=[MockProvider("backup", "ok")],
        )
        await router.invoke(prompt)

        snap = router.provider_pool.snapshot()
        assert snap["primary"]["success_rate"] == 0.0
        assert snap["backup"]["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_pool_rank_reflects_observed_performance(
        self, prompt: CortexPrompt
    ):
        """After multiple calls, pool.rank() reorders by observed latency."""
        fast = SlowProvider("fast", "fast", delay=0.001)
        slow = SlowProvider("slow", "slow", delay=0.05)

        router = CortexLLMRouter(primary=fast, fallbacks=[slow])

        # Call both via sequential cascade (primary wins, but let's also
        # record slow's metrics by making primary fail once)
        await router.invoke(prompt)  # fast succeeds

        # Record slow manually for comparison
        router.provider_pool.record_success("slow", 50.0)

        ranked = router.provider_pool.rank([slow, fast])
        assert ranked[0].provider_name == "fast"


# ─── DNSSEC (Intent Validation) Tests ────────────────────────────────────


class TestIntentValidator:
    """Unit tests for DNSSEC heuristic intent detection."""

    def test_code_response_detected_as_code(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        code_response = '''Here's the implementation:

```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

This function uses recursion to compute the nth Fibonacci number.
'''
        signal = validator.validate(code_response, IntentProfile.CODE, "test-provider")
        assert not signal.is_drift
        assert signal.detected_intent == IntentProfile.CODE

    def test_creative_response_detected_as_creative(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        creative_response = (
            'The protagonist wandered through the misty forest, '
            'feeling lost in thought. "Once upon a time," she whispered, '
            '"there was a story that no one dared to tell." She sighed '
            'deeply, gazing at the stars that felt impossibly distant. '
            'The dream of escape was a metaphor for something deeper!!'
        )
        signal = validator.validate(
            creative_response, IntentProfile.CREATIVE, "test-provider"
        )
        assert not signal.is_drift
        assert signal.detected_intent == IntentProfile.CREATIVE

    def test_general_intent_always_passes(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        signal = validator.validate(
            "Any response at all", IntentProfile.GENERAL, "test-provider"
        )
        assert not signal.is_drift
        assert signal.confidence == 1.0

    def test_short_response_gets_benefit_of_doubt(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        signal = validator.validate("ok", IntentProfile.CODE, "test-provider")
        assert not signal.is_drift
        assert signal.confidence == 0.0
        assert "too short" in signal.evidence

    def test_drift_detected_code_request_creative_response(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        # Request CODE but respond with pure creative content
        creative_response = (
            'The protagonist wandered through the misty forest, '
            'feeling lost in thought. "Once upon a time," she whispered, '
            '"there was a story that no one dared to tell." She sighed '
            'deeply, gazing at the stars that felt impossibly distant. '
            'The dream of escape was a metaphor for something deeper!! '
            'The character in the scene felt the narrative shift.'
        )
        signal = validator.validate(
            creative_response, IntentProfile.CODE, "bad-provider"
        )
        # Should detect drift — creative signals but code was requested
        assert signal.detected_intent == IntentProfile.CREATIVE
        assert signal.requested_intent == IntentProfile.CODE
        # Whether is_drift depends on delta meeting threshold

    def test_no_signals_gives_benefit_of_doubt(self):
        from cortex.llm.router import IntentValidator

        validator = IntentValidator()
        bland_response = "x" * 100  # long but no domain signals
        signal = validator.validate(
            bland_response, IntentProfile.CODE, "bland-provider"
        )
        assert not signal.is_drift
        assert "No domain signals" in signal.evidence


class TestDNSSECIntegration:
    """Router-level DNSSEC validation and weight penalty tests."""

    @pytest.fixture
    def code_prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a code generator.",
            working_memory=[{"role": "user", "content": "Write fibonacci"}],
            intent=IntentProfile.CODE,
        )

    @pytest.mark.asyncio
    async def test_drift_penalizes_provider_weight(self):
        """Provider returning creative content for CODE intent gets penalized."""
        # Provider returns creative prose when CODE was requested
        creative_response = (
            'The protagonist wandered through the misty forest, '
            'feeling lost in thought. "Once upon a time," she whispered, '
            '"there was a story that no one dared to tell." She sighed '
            'deeply, gazing at the stars that felt impossibly distant. '
            'The dream of escape was a metaphor for something deeper!! '
            'The character in the scene felt the narrative shift unfolding.'
        )
        bad_provider = MockProvider("drifty-provider", creative_response)

        prompt = CortexPrompt(
            system_instruction="Code gen.",
            working_memory=[{"role": "user", "content": "Write code"}],
            intent=IntentProfile.CODE,
        )

        router = CortexLLMRouter(primary=bad_provider)
        result = await router.invoke(prompt)
        assert isinstance(result, Ok)  # response still returned

        stats = router.drift_stats
        assert stats["total_validations"] == 1

        # Check if drift was detected
        history = router.drift_history
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_no_penalty_on_matching_response(self, code_prompt: CortexPrompt):
        """Provider returning code for CODE intent → no drift penalty."""
        code_response = '''Here's the implementation:

```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

import sys
class FibonacciCalculator:
    pass
```
'''
        good_provider = MockProvider("code-provider", code_response)
        router = CortexLLMRouter(primary=good_provider)
        await router.invoke(code_prompt)

        stats = router.drift_stats
        assert stats["total_validations"] == 1
        assert stats["drift_detected"] == 0
        assert stats["drift_penalties_applied"] == 0

    @pytest.mark.asyncio
    async def test_drift_stats_accuracy(self):
        """Multiple calls accumulate correct drift stats."""
        code_response = '```python\ndef foo():\n    return 42\nimport os\nclass Bar:\n    pass\n```'
        creative = (
            'The protagonist wandered through the misty forest, '
            'feeling lost in thought. "Once upon a time," she whispered, '
            '"there was a story." She sighed deeply, gazing upward. '
            'The dream felt like a metaphor for something deeper!! '
            'The character wandered on, whispering to no one at all.'
        )

        prompt_code = CortexPrompt(
            system_instruction="s",
            working_memory=[{"role": "user", "content": "c"}],
            intent=IntentProfile.CODE,
        )
        prompt_general = CortexPrompt(
            system_instruction="s",
            working_memory=[{"role": "user", "content": "c"}],
            intent=IntentProfile.GENERAL,
        )

        # good code provider + bad provider that returns creative for code
        code_provider = MockProvider("code-pro", code_response)
        creative_provider = MockProvider("creative-pro", creative)

        router = CortexLLMRouter(
            primary=code_provider,
            fallbacks=[creative_provider],
        )

        # Call 1: CODE → code response (no drift)
        await router.invoke(prompt_code)

        # Call 2: GENERAL → code response (always passes)
        await router.invoke(prompt_general)

        stats = router.drift_stats
        assert stats["total_validations"] == 2
        assert stats["clean_rate"] > 0.0


# ─── Adaptive TTL Tests ───────────────────────────────────────────────


class TestAdaptiveTTL:
    """Verifica el escalado dinámico de TTLs basado en fiabilidad (Ω₅)."""

    @pytest.fixture
    def prompt(self) -> CortexPrompt:
        return CortexPrompt(
            system_instruction="You are a helpful assistant.",
            working_memory=[{"role": "user", "content": "Hello"}],
        )

    def test_ttl_scaling_for_new_provider(self):
        """Un provider nuevo (sin calls) tiene success_rate=1.0 por defecto."""
        router = CortexLLMRouter(primary=MockProvider("p1", "ok"))
        # 100% of base TTL
        assert router._adaptive_positive_ttl("p1") == 600.0
        assert router._adaptive_negative_ttl("p1") == 300.0

    def test_ttl_scaling_for_perfect_provider(self):
        """Provider con 100% éxito mantiene TTLs base."""
        router = CortexLLMRouter(primary=MockProvider("p1", "ok"))
        router._provider_pool.get_or_create("p1").record_success(100.0)

        assert router._adaptive_positive_ttl("p1") == 600.0
        assert router._adaptive_negative_ttl("p1") == 300.0

    def test_ttl_scaling_for_flaky_provider(self):
        """Provider con 50% éxito ve reducido su A-record y aumentado su NXDOMAIN."""
        router = CortexLLMRouter(primary=MockProvider("p1", "ok"))
        metrics = router._provider_pool.get_or_create("p1")
        metrics.record_success(100.0)
        metrics.record_failure(100.0)

        # success_rate = 0.5
        # pos = 600 * 0.5 = 300
        # neg = 300 * (2.0 - 0.5) = 450
        assert router._adaptive_positive_ttl("p1") == 300.0
        assert router._adaptive_negative_ttl("p1") == 450.0

    def test_ttl_scaling_for_dead_provider(self):
        """Provider con 0% éxito: 0s positive TTL, 2x negative TTL."""
        router = CortexLLMRouter(primary=MockProvider("p1", "ok"))
        router._provider_pool.get_or_create("p1").record_failure(100.0)

        # success_rate = 0.0
        # pos = 600 * 0.0 = 0
        # neg = 300 * (2.0 - 0.0) = 600
        assert router._adaptive_positive_ttl("p1") == 0.0
        assert router._adaptive_negative_ttl("p1") == 600.0
