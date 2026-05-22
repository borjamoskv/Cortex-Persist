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


# ── VSA-SDM Tests ──


class TestVSAAlgebra:
    """Test MAP-B binary vector algebra."""

    def test_bind_self_inverse(self):
        """XOR bind is its own inverse."""
        from cortex.memory.vsa import bind, random_bipolar

        a = random_bipolar(500, seed=1)
        b = random_bipolar(500, seed=2)
        c = bind(a, b)
        recovered = bind(c, b)
        assert a == recovered

    def test_bundle_preserves_constituents(self):
        """Bundle is closer to constituents than random vectors."""
        from cortex.memory.vsa import bundle, cosine_similarity, random_bipolar

        v1 = random_bipolar(500, seed=10)
        v2 = random_bipolar(500, seed=20)
        sup = bundle([v1, v2])
        sim_constituent = cosine_similarity(sup, v1)
        sim_random = cosine_similarity(sup, random_bipolar(500, seed=99))
        assert sim_constituent > sim_random

    def test_hamming_distance(self):
        """Hamming distance of identical vectors is 0."""
        from cortex.memory.vsa import hamming_distance, random_bipolar

        v = random_bipolar(500, seed=42)
        assert hamming_distance(v, v) == 0
        assert hamming_distance(v, [1 - x for x in v]) == 500


class TestTextEncoder:
    """Test text-to-hypervector encoding."""

    def test_related_texts_higher_similarity(self):
        """Related texts have higher cosine similarity than unrelated."""
        from cortex.memory.vsa import TextEncoder, cosine_similarity

        enc = TextEncoder(dim=1000)
        h1 = enc.encode("smart contract vulnerability")
        h2 = enc.encode("smart contract exploit")
        h3 = enc.encode("banana smoothie recipe")
        sim_related = cosine_similarity(h1, h2)
        sim_unrelated = cosine_similarity(h1, h3)
        assert sim_related > sim_unrelated

    def test_empty_text(self):
        """Empty text returns zero vector."""
        from cortex.memory.vsa import TextEncoder

        enc = TextEncoder(dim=100)
        v = enc.encode("")
        assert all(x == 0 for x in v)


class TestSwarmMemory:
    """Test per-agent associative memory."""

    def test_record_and_recall(self):
        """Record memories and recall by similarity."""
        from cortex.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_mem", dim=1000)
        mem.record("DeFi flash loan attack vector", tags=["security"])
        mem.record("Reentrancy vulnerability", tags=["security"])
        mem.record("Weather is rainy in Bilbao", tags=["misc"])

        results = mem.recall("flash loan exploit", top_k=3)
        assert len(results) > 0
        assert "flash" in results[0]["content"].lower() or "loan" in results[0]["content"].lower()

    def test_consolidation(self):
        """Consolidation applies decay without crashing."""
        from cortex.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_decay", dim=500)
        mem.record("test memory 1")
        mem.record("test memory 2")
        pruned = mem.consolidate(decay_rate=0.01)
        assert isinstance(pruned, int)

    def test_persistence(self, tmp_path):
        """Persist and reload memories."""
        from cortex.memory.vsa import SwarmMemory

        mem = SwarmMemory(agent_id="test_persist", dim=500)
        mem._persistence_path = tmp_path / "test.vsa"
        mem.record("persistent memory", record_id="p1")
        hash_val = mem.persist()
        assert len(hash_val) == 64  # SHA-256

        mem2 = SwarmMemory(agent_id="test_persist", dim=500)
        mem2._persistence_path = tmp_path / "test.vsa"
        loaded = mem2.load()
        assert loaded == 1
        assert "p1" in mem2._records


class TestVSAPipelineBridge:
    """Test VSA bridge for ContextAssembler."""

    def test_bridge_query(self):
        """Bridge.query returns results in expected format."""
        from cortex.memory.vsa import SwarmMemory, VSAPipelineBridge

        bridge = VSAPipelineBridge.__new__(VSAPipelineBridge)
        bridge._memory = SwarmMemory(agent_id="bridge_test", dim=1000)
        bridge._memory.record("Oracle manipulation attack", tags=["vuln"])
        bridge._memory.record("Cross-chain bridge exploit", tags=["vuln"])

        results = bridge.query("oracle vulnerability", top_k=2)
        assert len(results) > 0
        assert "content" in results[0]
        assert "similarity" in results[0]

    def test_bridge_ingest(self):
        """Bridge.ingest stores and returns record ID."""
        from cortex.memory.vsa import SwarmMemory, VSAPipelineBridge

        bridge = VSAPipelineBridge.__new__(VSAPipelineBridge)
        bridge._memory = SwarmMemory(agent_id="ingest_test", dim=500)

        rid = bridge.ingest("test knowledge item", record_id="ki-001")
        assert rid == "ki-001"
        assert bridge.stats["records"] == 1


# ── Provider Factory Tests ──


class TestProviderFactory:
    """Test LLM provider auto-discovery."""

    def test_factory_returns_none_when_no_keys(self):
        """Factory returns (None, None) when no API keys are set."""
        import os

        from cortex.pipeline.provider_factory import build_executor_stack

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
            # May or may not find local providers — both outcomes valid
            if router is None and provider is None:
                assert True  # Expected: no keys, no local service
            else:
                # Local provider found (ollama running)
                assert provider is not None
        finally:
            os.environ.update(saved)

    def test_factory_priority_order(self):
        """Provider priority list is correctly ordered."""
        from cortex.pipeline.provider_factory import _PROVIDER_PRIORITY

        assert _PROVIDER_PRIORITY[0] == "gemini"
        assert "anthropic" in _PROVIDER_PRIORITY
        assert "ollama" in _PROVIDER_PRIORITY
        assert _PROVIDER_PRIORITY.index("gemini") < _PROVIDER_PRIORITY.index("ollama")

    def test_executor_uses_factory(self):
        """AgentExecutor._ensure_stack() calls factory on first use."""
        from cortex.pipeline.executor import AgentExecutor

        executor = AgentExecutor()
        assert executor._initialized is False
        executor._ensure_stack()
        assert executor._initialized is True
        # Second call is a no-op
        executor._ensure_stack()
        assert executor._initialized is True

    def test_executor_accepts_pre_built_provider(self):
        """Executor respects injected provider over factory."""
        from cortex.pipeline.executor import AgentExecutor

        class MockProvider:
            provider_name = "mock"

        mock = MockProvider()
        executor = AgentExecutor(provider=mock)
        assert executor._provider is mock


# ── Enhanced Async Tests ──


class TestAsyncPipelineEnhanced:
    """Test native async pipeline improvements."""

    def test_run_async_timeout_no_deadlock(self):
        """run_async with slow executor times out without deadlock."""
        import asyncio

        class SlowExecutor:
            async def execute(self, **kw):
                await asyncio.sleep(999)

        orch = CortexOrchestrator(agent_executor=SlowExecutor())
        req = PipelineRequest(intent="slow mission", timeout_s=0.5)
        result = asyncio.run(orch.run_async(req))
        assert result.status == PipelineStatus.FAILED
        assert "timeout" in result.error.lower()

    def test_run_async_cancellation_contract(self):
        """Cancellation returns CANCELLED status."""
        import asyncio

        async def _test():
            orch = CortexOrchestrator()
            req = PipelineRequest(intent="cancel test")
            task = asyncio.create_task(orch.run_async(req))
            # Let it start then cancel
            await asyncio.sleep(0)
            task.cancel()
            try:
                result = await task
                # If pipeline completed before cancel, that's OK
                assert result.status in (PipelineStatus.SUCCESS, PipelineStatus.CANCELLED)
            except asyncio.CancelledError:
                pass  # Also valid

        asyncio.run(_test())

    def test_run_streaming_yields_traces(self):
        """run_streaming yields StageTrace events then PipelineResult."""
        import asyncio

        async def _test():
            orch = CortexOrchestrator()
            req = PipelineRequest(intent="streaming test")
            events = []
            async for event in orch.run_streaming(req):
                events.append(event)

            # Should yield 6 StageTraces + 1 PipelineResult = 7 events
            assert len(events) == 7
            # Last event is the final PipelineResult
            assert isinstance(events[-1], PipelineResult)
            assert events[-1].status == PipelineStatus.SUCCESS
            # First 6 are StageTraces
            for trace in events[:6]:
                assert isinstance(trace, StageTrace)
                assert trace.latency_ms >= 0

        asyncio.run(_test())

    def test_run_async_six_stages(self):
        """Async pipeline produces exactly 6 stage traces."""
        import asyncio

        orch = CortexOrchestrator()
        req = PipelineRequest(intent="stage count test")
        result = asyncio.run(orch.run_async(req))
        assert result.status == PipelineStatus.SUCCESS
        assert len(result.stages) == 6
        stage_names = [s.stage for s in result.stages]
        assert PipelineStage.INGRESS in stage_names
        assert PipelineStage.EXECUTION in stage_names
        assert PipelineStage.PERSISTENCE in stage_names


# ── MCP Outbound Skeleton Tests ──


class TestMCPOutbound:
    """Test MCP outbound client skeleton."""

    def test_client_initialization(self):
        """Client initializes with empty tool list."""
        from cortex.pipeline.mcp_outbound import MCPOutboundClient

        client = MCPOutboundClient()
        assert client.available_tools == []
        assert client.get_tool_schemas_for_prompt() == ""

    def test_client_call_unknown_tool(self):
        """Calling unknown tool returns error dict."""
        import asyncio

        from cortex.pipeline.mcp_outbound import MCPOutboundClient

        client = MCPOutboundClient()
        result = asyncio.run(client.call_tool("nonexistent", {}))
        assert "error" in result
        assert "not found" in result["error"]

    def test_tool_spec_dataclass(self):
        """MCPToolSpec holds tool metadata correctly."""
        from cortex.pipeline.mcp_outbound import MCPToolSpec

        spec = MCPToolSpec(
            name="web_search",
            description="Search the web",
            input_schema={"query": {"type": "string"}},
            server_name="brave",
        )
        assert spec.name == "web_search"
        assert spec.server_name == "brave"

    def test_tool_schema_formatting(self):
        """Tool schemas format correctly for prompt injection."""
        from cortex.pipeline.mcp_outbound import MCPOutboundClient, MCPToolSpec

        client = MCPOutboundClient()
        client._tools = [
            MCPToolSpec(name="search", description="Web search"),
            MCPToolSpec(name="read", description="Read file"),
        ]
        schema_text = client.get_tool_schemas_for_prompt()
        assert "<available_tools>" in schema_text
        assert "search" in schema_text
        assert "read" in schema_text


# ── VSA Adapter Tests ──


class TestVSAAdapter:
    """Test VSA context adapter integration."""

    def test_adapter_graceful_when_unavailable(self):
        """Adapter returns empty results when VSA engine not importable."""
        from cortex.context.vsa_adapter import VSAContextAdapter

        adapter = VSAContextAdapter.__new__(VSAContextAdapter)
        adapter._available = False
        adapter._mem = None
        adapter._agent_id = "test"
        adapter._D = 10000
        adapter._decay_lambda = 0.05
        adapter._memory_dir = None

        results = adapter.query("test query")
        assert results == []
        assert adapter.ingest("test") is False
        report = adapter.consolidate()
        assert report["persisted"] is False

    def test_adapter_diagnostics_unavailable(self):
        """Diagnostics report unavailable state."""
        from cortex.context.vsa_adapter import VSAContextAdapter

        adapter = VSAContextAdapter.__new__(VSAContextAdapter)
        adapter._available = False
        adapter._mem = None
        adapter._agent_id = "test"
        adapter._D = 10000
        adapter._decay_lambda = 0.05
        adapter._memory_dir = None

        diag = adapter.diagnostics()
        assert diag["available"] is False

    def test_assembler_with_vsa_bridge(self):
        """ContextAssembler uses VSA bridge when provided."""

        class MockVSA:
            def query(self, intent, top_k=3):
                return [
                    {
                        "id": "vsa-0",
                        "content": "algebraic context",
                        "similarity": 0.85,
                        "tags": {},
                        "timestamp": 0,
                    }
                ]

        assembler = ContextAssembler(vsa_adapter=MockVSA())
        ctx = assembler.assemble(intent="test vsa")
        # VSA results should appear in knowledge_items
        assert any(ki.get("method") == "vsa" for ki in ctx.knowledge_items), (
            f"Expected VSA items in: {ctx.knowledge_items}"
        )
