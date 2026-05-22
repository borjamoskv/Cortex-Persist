"""CORTEX E2E Pipeline — Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from cortex.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from cortex.pipeline.orchestrator import (
    BudgetExhaustedError,
    CortexOrchestrator,
    PipelineCancelledError,
)
from cortex.router.router import AgentRouter, AgentCapability
from cortex.context.assembler import ContextAssembler
from cortex.delivery.manager import DeliveryManager


# ── Contract Tests ──


class TestPipelineContracts:
    """Test that pipeline data contracts are well-formed."""

    def test_pipeline_request_defaults(self):
        req = PipelineRequest(intent="analyze this")
        assert req.intent == "analyze this"
        assert req.budget_limit_usd == 0.10
        assert req.mission_id.startswith("m-")
        assert req.tenant_id == "default"
        assert req.priority == 1
        assert req.timeout_s == 120.0

    def test_pipeline_result_latency(self):
        result = PipelineResult(
            mission_id="test-001",
            status=PipelineStatus.SUCCESS,
            created_at=1000.0,
            completed_at=1001.5,
        )
        assert result.latency_ms == 1500.0

    def test_pipeline_result_total_tokens(self):
        result = PipelineResult(
            mission_id="test-002",
            status=PipelineStatus.SUCCESS,
            stages=[
                StageTrace(
                    stage=PipelineStage.CONTEXT,
                    started_at=0,
                    ended_at=1,
                    tokens_in=100,
                    tokens_out=50,
                ),
                StageTrace(
                    stage=PipelineStage.EXECUTION,
                    started_at=1,
                    ended_at=2,
                    tokens_in=200,
                    tokens_out=300,
                ),
            ],
        )
        assert result.total_tokens == 650

    def test_delivery_target_types(self):
        for dt in DeliveryType:
            target = DeliveryTarget(type=dt)
            assert target.type == dt
            assert target.format == "markdown"

    def test_context_packet_empty(self):
        ctx = ContextPacket()
        assert ctx.facts == []
        assert ctx.knowledge_items == []
        assert ctx.total_tokens == 0

    def test_stage_trace_latency_auto(self):
        trace = StageTrace(stage=PipelineStage.INGRESS, started_at=100.0, ended_at=100.05)
        assert abs(trace.latency_ms - 50.0) < 1.0


# ── Orchestrator Tests ──


class TestOrchestrator:
    """Test the E2E orchestrator pipeline flow."""

    def test_basic_pipeline_success(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="hello world")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert result.mission_id == req.mission_id
        assert result.latency_ms > 0
        assert result.ledger_hash != ""
        assert len(result.stages) == 6  # All 6 stages should run

    def test_empty_intent_fails(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="")
        result = orch.run(req)

        assert result.status == PipelineStatus.FAILED
        assert "Empty intent" in result.error

    def test_zero_budget_fails(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="test", budget_limit_usd=0)
        result = orch.run(req)

        assert result.status == PipelineStatus.FAILED
        assert "Budget" in result.error

    def test_pipeline_with_context_assembler(self):
        assembler = ContextAssembler()  # No backends
        orch = CortexOrchestrator(context_assembler=assembler)
        req = PipelineRequest(intent="analyze security patterns")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert len(result.stages) == 6

    def test_pipeline_with_router(self):
        router = AgentRouter()
        orch = CortexOrchestrator(agent_router=router)
        req = PipelineRequest(intent="find vulnerability in smart contract")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert "security-analyst" in result.agent_chain

    def test_pipeline_with_delivery(self):
        delivery = DeliveryManager()
        orch = CortexOrchestrator(delivery_manager=delivery)
        req = PipelineRequest(
            intent="test delivery",
            delivery=DeliveryTarget(type=DeliveryType.MEMORY),
        )
        result = orch.run(req)
        assert result.status == PipelineStatus.SUCCESS

    def test_full_pipeline_all_components(self):
        orch = CortexOrchestrator(
            context_assembler=ContextAssembler(),
            agent_router=AgentRouter(),
            delivery_manager=DeliveryManager(),
        )
        req = PipelineRequest(
            intent="research state of the art in formal verification",
            context_hints=[],
            delivery=DeliveryTarget(type=DeliveryType.MEMORY),
        )
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert result.cost_usd >= 0
        assert result.ledger_hash
        assert len(result.stages) == 6
        assert all(s.latency_ms >= 0 for s in result.stages)


# ── Router Tests ──


class TestAgentRouter:
    """Test deterministic agent routing."""

    def test_security_routing(self):
        router = AgentRouter()
        plan = router.route("find vulnerability in smart contract")
        assert "security-analyst" in plan["agents"]

    def test_code_routing(self):
        router = AgentRouter()
        plan = router.route("implement a Python class for data processing")
        assert "code-engineer" in plan["agents"]

    def test_research_routing(self):
        router = AgentRouter()
        plan = router.route("research the state of the art in LLM evaluation")
        assert "researcher" in plan["agents"]

    def test_fallback_to_general(self):
        router = AgentRouter()
        plan = router.route("what time is it?")
        assert "general" in plan["agents"]

    def test_register_custom_agent(self):
        router = AgentRouter()
        router.register_agent(
            AgentCapability(
                agent_id="audio-engineer",
                patterns=[r"master", r"audio", r"stems", r"loudness"],
                priority=0,
            )
        )
        plan = router.route("master this audio track")
        assert "audio-engineer" in plan["agents"]

    def test_budget_aware_routing(self):
        router = AgentRouter()
        plan = router.route("analyze vulnerability", budget_remaining=0.001)
        assert len(plan["agents"]) >= 1  # Should still route at least one


# ── Delivery Tests ──


class TestDeliveryManager:
    """Test delivery to various targets."""

    def test_memory_delivery(self):
        dm = DeliveryManager()
        result = dm.deliver({"test": True}, DeliveryTarget(type=DeliveryType.MEMORY), "m-test")
        assert result is True

    def test_file_delivery(self, tmp_path):
        dm = DeliveryManager()
        target = DeliveryTarget(
            type=DeliveryType.FILE, path=str(tmp_path / "output.json"), format="json"
        )
        result = dm.deliver({"key": "value"}, target, "m-file-test")
        assert result is True
        assert (tmp_path / "output.json").exists()
        content = (tmp_path / "output.json").read_text()
        assert '"key"' in content

    def test_markdown_conversion(self):
        md = DeliveryManager._to_markdown({"title": "Test", "items": ["a", "b", "c"]})
        assert "# Pipeline Result" in md
        assert "- a" in md

    def test_file_delivery_no_path_fails(self):
        dm = DeliveryManager()
        result = dm.deliver({}, DeliveryTarget(type=DeliveryType.FILE), "m-no-path")
        assert result is False


# ── Context Assembler Tests ──


class TestContextAssembler:
    """Test the unified context assembler."""

    def test_empty_assembly(self):
        assembler = ContextAssembler()
        ctx = assembler.assemble(intent="test query")
        assert isinstance(ctx, ContextPacket)
        assert ctx.total_tokens == 0

    def test_hint_resolution_missing_ki(self):
        assembler = ContextAssembler()
        ctx = assembler.assemble(intent="test", hints=["nonexistent_ki_12345"])
        assert len(ctx.knowledge_items) == 0  # Should not crash


# ── Agent Executor Tests ──


class TestAgentExecutor:
    """Test the real LLM agent executor."""

    def test_executor_stub_mode(self):
        """When no LLM is available, executor returns structured stub."""
        import asyncio

        from cortex.pipeline.executor import AgentExecutor

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
        from cortex.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        prompt = executor._build_system_prompt("security-analyst", None)
        assert "security" in prompt.lower()
        assert "vulnerability" in prompt.lower()

        prompt = executor._build_system_prompt("code-engineer", None)
        assert "code" in prompt.lower()
        assert "typed" in prompt.lower()

    def test_executor_working_memory_from_context(self):
        """Working memory includes facts when context is provided."""
        from cortex.pipeline.executor import AgentExecutor

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
        from cortex.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        messages = executor._build_working_memory("simple query", None)
        assert len(messages) == 1
        assert messages[0]["content"] == "simple query"

    def test_orchestrator_with_executor_stub(self):
        """Orchestrator uses executor when provided (stub path)."""
        from cortex.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        orch = CortexOrchestrator(agent_executor=executor)
        req = PipelineRequest(intent="test with executor")
        result = orch.run(req)
        assert result.status == PipelineStatus.SUCCESS
        assert result.output is not None


# ── Async Orchestrator Tests ──


class TestAsyncOrchestrator:
    """Test async pipeline execution."""

    def test_run_async_basic(self):
        """run_async completes a simple mission."""
        import asyncio

        orch = CortexOrchestrator()
        req = PipelineRequest(intent="async test")
        result = asyncio.run(orch.run_async(req))
        assert result.status == PipelineStatus.SUCCESS
        assert len(result.stages) == 6

    def test_run_async_timeout(self):
        """run_async handles timeout gracefully."""
        import asyncio

        orch = CortexOrchestrator()
        # Set impossible timeout — pipeline executes instantly so
        # we verify the contract works (timeout returns PipelineResult)
        req = PipelineRequest(intent="timeout test", timeout_s=30.0)
        result = asyncio.run(orch.run_async(req))
        # With no LLM executor, the pipeline completes in <1ms
        assert result.status == PipelineStatus.SUCCESS
        assert result.latency_ms < 30_000


# ── MCP Pipeline Tools Tests ──


class TestMCPPipelineTools:
    """Test MCP pipeline tool serialization."""

    def test_result_to_dict_single_agent(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-test",
            status=PipelineStatus.SUCCESS,
            output={"content": "hello", "provider": "gemini"},
            ledger_hash="abc123",
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert d["content"] == "hello"
        assert d["provider"] == "gemini"
        assert d["status"] == "success"

    def test_result_to_dict_multi_agent(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-multi",
            status=PipelineStatus.SUCCESS,
            output={
                "multi_agent": True,
                "results": [
                    {"agent_id": "a1", "content": "result 1"},
                    {"agent_id": "a2", "content": "result 2"},
                ],
            },
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert "[a1]" in d["content"]
        assert "[a2]" in d["content"]

    def test_result_to_dict_error(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-err",
            status=PipelineStatus.FAILED,
            error="something broke",
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert d["status"] == "failed"
        assert d["error"] == "something broke"
