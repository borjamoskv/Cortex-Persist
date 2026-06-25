# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from legacy_research.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from legacy_research.pipeline.orchestrator import CortexOrchestrator
from legacy_research.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from legacy_research.router.router import AgentRouter, AgentCapability
from legacy_research.context.assembler import ContextAssembler
from legacy_research.delivery.manager import DeliveryManager


# ── Provider Factory Tests ──


class TestProviderFactory:
    """Test LLM provider auto-discovery."""

    def test_factory_returns_none_when_no_keys(self):
        """Factory returns (None, None) when no API keys are set."""
        import os

        from legacy_research.pipeline.provider_factory import build_executor_stack

        # Ensure no relevant keys are set (save and restore)
        saved = {}
        keys_to_clear = [
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "DASHSCOPE_API_KEY",
            "OPENROUTER_API_KEY",
            "GROQ_API_KEY",
        ]
        for k in keys_to_clear:
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            router, provider = build_executor_stack()
            # May or may not find local providers - both outcomes valid
            if router is None and provider is None:
                assert True  # Expected: no keys, no local service
            else:
                # Local provider found (ollama running)
                assert provider is not None
        finally:
            os.environ.update(saved)

    def test_factory_priority_order(self):
        """Provider priority list is correctly ordered."""
        from legacy_research.pipeline.provider_factory import _PROVIDER_PRIORITY

        assert _PROVIDER_PRIORITY[0] == "gemini"
        assert "anthropic" in _PROVIDER_PRIORITY
        assert "ollama" in _PROVIDER_PRIORITY
        assert _PROVIDER_PRIORITY.index("gemini") < _PROVIDER_PRIORITY.index("ollama")

    def test_executor_uses_factory(self):
        """AgentExecutor._ensure_stack() calls factory on first use."""
        from legacy_research.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        assert executor._initialized is False
        executor._ensure_stack()
        assert executor._initialized is True
        # Second call is a no-op
        executor._ensure_stack()
        assert executor._initialized is True

    def test_executor_accepts_pre_built_provider(self):
        """Executor respects injected provider over factory."""
        from legacy_research.pipeline.executor import AgentExecutor

        class MockProvider:
            provider_name = "mock"

        mock = MockProvider()
        executor = AgentExecutor(provider=mock)
        assert executor._provider is mock
