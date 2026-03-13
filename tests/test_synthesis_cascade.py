"""Tests for AUTODIDACT synthesis cascade — Ω₅ Antifragile verification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.llm._models import IntentProfile
from cortex.llm.router import CortexLLMRouter
from cortex.utils.result import Ok

# ─── Helper: build a fake router ──────────────────────────────────────────────


def _mock_provider(name: str = "mock-primary") -> MagicMock:
    p = MagicMock()
    p.provider_name = name
    p.model_name = "mock-model"
    p.intent_affinity = frozenset({IntentProfile.GENERAL})
    return p


class TestGetSynthesisRouter:
    """Verify _get_synthesis_router builds correctly."""

    def test_router_returned_when_providers_exist(self):
        """Ω₅: With at least one available provider, the router builds."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        mock_prov = _mock_provider("qwen")

        with patch.object(syn, "LLMProvider", side_effect=[mock_prov, ValueError("no key")]):
            with patch.object(syn, "_SYNTHESIS_PROVIDERS", ("qwen", "bad")):
                router = syn._get_synthesis_router()

        assert router is not None
        assert router.primary is mock_prov
        syn._synthesis_router = None  # cleanup

    def test_router_raises_when_no_providers(self):
        """Ω₃: Raises RuntimeError when ALL providers lack keys."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        with patch.object(syn, "LLMProvider", side_effect=ValueError("no key")):
            with pytest.raises(RuntimeError, match="No LLM providers"):
                syn._get_synthesis_router()

        syn._synthesis_router = None  # cleanup

    def test_router_is_singleton(self):
        """Lazy singleton — same instance on repeated calls."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        mock_prov = _mock_provider()
        with patch.object(syn, "LLMProvider", return_value=mock_prov):
            with patch.object(syn, "_SYNTHESIS_PROVIDERS", ("qwen",)):
                r1 = syn._get_synthesis_router()
                r2 = syn._get_synthesis_router()

        assert r1 is r2
        syn._synthesis_router = None  # cleanup


class TestDistillSovereignMemo:
    """Verify distill_sovereign_memo routes through the cascade."""

    @pytest.mark.asyncio
    async def test_distill_does_not_require_anthropic_key(self):
        """The refactored pipeline must NOT fail with ANTHROPIC_API_KEY missing."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        mock_router = MagicMock(spec=CortexLLMRouter)
        mock_router.execute_resilient = AsyncMock(
            return_value=Ok(
                '{"content_markdown": "Test crystal", '
                '"entities": ["Python"], '
                '"resonancia_axiomatica": "Ω₂ verified"}'
            )
        )

        with patch.object(syn, "_get_synthesis_router", return_value=mock_router):
            result = await syn.distill_sovereign_memo(
                raw_data="Test raw data about Python agents",
                source_url="https://example.com",
                intent="Extract agent patterns",
            )

        # sovereign_circuit_breaker wraps in {status, data}
        inner = result["data"] if isinstance(result, dict) and "data" in result else result
        assert inner["content_markdown"] == "Test crystal"
        assert "Python" in inner["entities"]

        # Verify the prompt used IntentProfile.REASONING
        call_args = mock_router.execute_resilient.call_args
        prompt = call_args[0][0]
        assert prompt.intent == IntentProfile.REASONING

    @pytest.mark.asyncio
    async def test_intent_directive_is_injected(self):
        """The intent laser directive must appear in the system prompt."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        mock_router = MagicMock(spec=CortexLLMRouter)
        mock_router.execute_resilient = AsyncMock(
            return_value=Ok('{"content_markdown": "x", "entities": []}')
        )

        with patch.object(syn, "_get_synthesis_router", return_value=mock_router):
            await syn.distill_sovereign_memo(
                raw_data="data" * 100,  # needs some content
                source_url="https://example.com",
                intent="Focus on Redis optimization",
            )

        call_args = mock_router.execute_resilient.call_args
        prompt = call_args[0][0]
        assert "ENFOQUE LÁSER" in prompt.system_instruction
        assert "Redis optimization" in prompt.system_instruction

    @pytest.mark.asyncio
    async def test_general_mode_when_no_intent(self):
        """Without an intent, should use GENERAL extraction mode."""
        import cortex.skills.autodidact.synthesis as syn

        syn._synthesis_router = None

        mock_router = MagicMock(spec=CortexLLMRouter)
        mock_router.execute_resilient = AsyncMock(
            return_value=Ok('{"content_markdown": "x", "entities": []}')
        )

        with patch.object(syn, "_get_synthesis_router", return_value=mock_router):
            await syn.distill_sovereign_memo(
                raw_data="data" * 100,
                source_url="https://example.com",
                intent="",
            )

        call_args = mock_router.execute_resilient.call_args
        prompt = call_args[0][0]
        assert "ENFOQUE GENERAL" in prompt.system_instruction
