"""Tests for cortex.llm.router — ROP-based LLM routing."""

from __future__ import annotations

import pytest

from cortex.llm.router import BaseProvider, CortexLLMRouter, CortexPrompt
from cortex.result import Err, Ok

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
