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




# ─── Positive Cache (DNS A-Record) Tests ─────────────────────────────────────




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




# ─── DNSSEC (Intent Validation) Tests ────────────────────────────────────




# ─── Adaptive TTL Tests ───────────────────────────────────────────────


