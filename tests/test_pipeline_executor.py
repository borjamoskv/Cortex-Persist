# [C5-REAL] Exergy-Maximized
"""Tests for cortex.pipeline.executor - Agent Executor (stub mode).

C5-REAL audit remediation: pipeline/ coverage gap.
Tests the executor in stub mode (no LLM infrastructure required)
and the prompt-building logic.
"""

from __future__ import annotations

import pytest

from legacy_research.pipeline import ContextPacket
from legacy_research.pipeline.executor import AgentExecutor


# ── Construction ─────────────────────────────────────────────────────────


class TestConstruction:
    def test_default_init(self):
        ex = AgentExecutor()
        assert ex._provider_name == "gemini"
        assert ex._initialized is False

    def test_custom_provider_name(self):
        ex = AgentExecutor(provider_name="openai")
        assert ex._provider_name == "openai"


# ── System Prompt Building ───────────────────────────────────────────────


class TestSystemPrompt:
    def test_known_agent_id(self):
        ex = AgentExecutor()
        prompt = ex._build_system_prompt("security-analyst", None)
        assert "security" in prompt.lower()
        assert "vulnerability" in prompt.lower()

    def test_unknown_agent_falls_back_to_general(self):
        ex = AgentExecutor()
        prompt = ex._build_system_prompt("nonexistent-agent", None)
        assert "CORTEX" in prompt

    def test_context_injected(self):
        ex = AgentExecutor()
        ctx = ContextPacket(
            knowledge_items=[{"source": "test_ki", "content": "important context data"}]
        )
        prompt = ex._build_system_prompt("general", ctx)
        assert "test_ki" in prompt
        assert "<context>" in prompt

    def test_no_context_no_injection(self):
        ex = AgentExecutor()
        prompt = ex._build_system_prompt("general", None)
        assert "<context>" not in prompt

    def test_all_profiles_exist(self):
        ex = AgentExecutor()
        agents = [
            "security-analyst",
            "code-engineer",
            "researcher",
            "architect",
            "creative",
            "general",
        ]
        for agent_id in agents:
            prompt = ex._build_system_prompt(agent_id, None)
            assert len(prompt) > 50, f"Profile for {agent_id} seems too short"


# ── Working Memory Building ──────────────────────────────────────────────


class TestWorkingMemory:
    def test_intent_always_included(self):
        ex = AgentExecutor()
        messages = ex._build_working_memory("test intent", None)
        assert len(messages) >= 1
        assert messages[-1]["content"] == "test intent"
        assert messages[-1]["role"] == "user"

    def test_facts_included_when_present(self):
        ex = AgentExecutor()
        ctx = ContextPacket(
            facts=[
                {"content": "fact one", "confidence": "high"},
                {"content": "fact two", "confidence": "medium"},
            ]
        )
        messages = ex._build_working_memory("test intent", ctx)
        assert len(messages) == 2  # facts + intent
        assert "relevant_facts" in messages[0]["content"]
        assert "fact one" in messages[0]["content"]

    def test_no_facts_no_extra_message(self):
        ex = AgentExecutor()
        ctx = ContextPacket(facts=[])
        messages = ex._build_working_memory("test intent", ctx)
        assert len(messages) == 1


# ── Execute (Stub Mode) ─────────────────────────────────────────────────


class TestExecuteStub:
    @staticmethod
    def _make_stub_executor() -> AgentExecutor:
        """Create an executor with _execute_single_agent mocked to return stub data."""
        ex = AgentExecutor()
        ex._initialized = True

        async def _stub_single(agent_id, intent, context, budget_remaining):
            return {
                "content": f"[STUB] Agent '{agent_id}' executed for: {intent[:50]}",
                "tokens": 0,
                "cost_usd": 0.0,
                "provider": "stub",
            }

        ex._execute_single_agent = _stub_single
        return ex

    @pytest.mark.asyncio
    async def test_single_agent_stub(self):
        ex = self._make_stub_executor()
        result = await ex.execute(
            intent="test query",
            plan={"agents": ["general"]},
        )
        assert result["agent_id"] == "general"
        assert result["provider"] == "stub"
        assert "STUB" in result["content"]

    @pytest.mark.asyncio
    async def test_multi_agent_stub(self):
        ex = self._make_stub_executor()
        result = await ex.execute(
            intent="test query",
            plan={"agents": ["general", "researcher"]},
        )
        assert result["multi_agent"] is True
        assert len(result["results"]) == 2
        assert result["total_tokens"] == 0
        assert result["total_cost_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_default_plan_uses_general(self):
        ex = self._make_stub_executor()
        result = await ex.execute(intent="test query", plan=None)
        assert result["agent_id"] == "general"

    @pytest.mark.asyncio
    async def test_agent_failure_captured(self):
        ex = AgentExecutor()
        ex._initialized = True

        async def _failing_agent(agent_id, intent, context, budget_remaining):
            raise RuntimeError("LLM unreachable")

        ex._execute_single_agent = _failing_agent
        result = await ex.execute(
            intent="test query",
            plan={"agents": ["general"]},
        )
        assert result["status"] == "failed"
        assert "LLM unreachable" in result["error"]

    @pytest.mark.asyncio
    async def test_close_without_provider(self):
        ex = AgentExecutor()
        # Should not raise
        await ex.close()

    @pytest.mark.asyncio
    async def test_ensure_stack_idempotent(self):
        ex = AgentExecutor()
        ex._ensure_stack()
        assert ex._initialized is True
        # Second call should be no-op
        ex._ensure_stack()
        assert ex._initialized is True
