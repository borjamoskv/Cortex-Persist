# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from babylon60.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from babylon60.pipeline.orchestrator import CortexOrchestrator
from babylon60.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from babylon60.router.router import AgentRouter, AgentCapability
from babylon60.context.assembler import ContextAssembler
from babylon60.delivery.manager import DeliveryManager


# ── Agent Executor Tests ──


class TestAgentExecutor:
    """Test the real LLM agent executor."""

    def test_executor_stub_mode(self):
        """When no LLM is available, executor returns structured stub."""
        import asyncio

        from babylon60.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        # Force stub path by preventing provider init
        executor._provider = None
        executor._router = None

        async def _mock_ensure_none():
            return None

        executor._ensure_provider = _mock_ensure_none
        executor._ensure_router = _mock_ensure_none

        result = asyncio.run(executor.execute(intent="test intent"))
        assert result.get("provider") == "stub"
        assert "content" in result

    def test_executor_system_prompt_construction(self):
        """System prompts contain agent-specific instructions."""
        from babylon60.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        prompt = executor._build_system_prompt("security-analyst", None)
        assert "security" in prompt.lower()
        assert "vulnerability" in prompt.lower()

        prompt = executor._build_system_prompt("code-engineer", None)
        assert "code" in prompt.lower()
        assert "typed" in prompt.lower()

    def test_executor_working_memory_from_context(self):
        """Working memory includes facts when context is provided."""
        from babylon60.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        ctx = ContextPacket(
            facts=[
                {"content": "fact one", "confidence": "C5"},
                {"content": "fact two", "confidence": "C4"},
            ]
        )
        messages = executor._build_working_memory("analyze this", ctx)
        assert len(messages) >= 2  # facts + intent
        assert messages[-1]["content"] == "analyze this"
        assert "relevant_facts" in messages[0]["content"]

    def test_executor_working_memory_no_context(self):
        """Working memory contains only intent when no context."""
        from babylon60.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        messages = executor._build_working_memory("simple query", None)
        assert len(messages) == 1
        assert messages[0]["content"] == "simple query"

    def test_orchestrator_with_executor_stub(self):
        """Orchestrator uses executor when provided (stub path)."""
        from babylon60.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        executor._provider = None
        executor._router = None

        async def _mock_ensure_none():
            return None

        executor._ensure_provider = _mock_ensure_none
        executor._ensure_router = _mock_ensure_none

        orch = CortexOrchestrator(agent_executor=executor)
        req = PipelineRequest(intent="test with executor")
        result = orch.run(req)
        assert result.status == PipelineStatus.SUCCESS
        assert result.output is not None
