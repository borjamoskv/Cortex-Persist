# [C5-REAL] Exergy-Maximized
"""Tests for babylon60.pipeline.orchestrator - Sovereign E2E Pipeline.

C5-REAL audit remediation: pipeline/ coverage gap.
Tests the synchronous `run()` path and all 6 stage implementations
using mock dependencies to avoid LLM/DB calls.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

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


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_request(**overrides) -> PipelineRequest:
    defaults = {
        "intent": "test intent",
        "mission_id": "m-test-001",
        "budget_limit_usd": 1.0,
        "timeout_s": 30.0,
    }
    defaults.update(overrides)
    return PipelineRequest(**defaults)


# ── Ingress Validation ───────────────────────────────────────────────────


class TestIngress:
    def test_empty_intent_raises(self):
        orch = CortexOrchestrator()
        with pytest.raises(ValueError, match="Empty intent"):
            orch._ingress(_make_request(intent=""))

    def test_whitespace_intent_raises(self):
        orch = CortexOrchestrator()
        with pytest.raises(ValueError, match="Empty intent"):
            orch._ingress(_make_request(intent="   "))

    def test_zero_budget_raises(self):
        orch = CortexOrchestrator()
        with pytest.raises(ValueError, match="Budget"):
            orch._ingress(_make_request(budget_limit_usd=0))

    def test_negative_timeout_raises(self):
        orch = CortexOrchestrator()
        with pytest.raises(ValueError, match="Timeout"):
            orch._ingress(_make_request(timeout_s=-1))

    def test_valid_request_passes(self):
        orch = CortexOrchestrator()
        # Should not raise
        orch._ingress(_make_request())


# ── Context Assembly ─────────────────────────────────────────────────────


class TestContextAssembly:
    def test_no_assembler_returns_empty_context(self):
        orch = CortexOrchestrator(context_assembler=None)
        result = orch._assemble_context(_make_request())
        assert isinstance(result, ContextPacket)
        assert result.facts == []
        assert result.knowledge_items == []

    def test_assembler_called(self):
        class MockAssembler:
            def assemble(self, intent, hints, tenant_id):
                return ContextPacket(
                    facts=[{"content": "test fact"}],
                    knowledge_items=[{"source": "test_ki"}],
                )

        orch = CortexOrchestrator(context_assembler=MockAssembler())
        result = orch._assemble_context(_make_request())
        assert len(result.facts) == 1
        assert result.knowledge_items[0]["source"] == "test_ki"


# ── Planning ─────────────────────────────────────────────────────────────


class TestPlanning:
    def test_no_router_returns_default_plan(self):
        orch = CortexOrchestrator(agent_router=None)
        plan = orch._plan(_make_request(), ContextPacket())
        assert plan["agents"] == ["general"]
        assert plan["strategy"] == "sequential"

    def test_router_called(self):
        class MockRouter:
            def route(self, intent, context, budget_remaining):
                return {
                    "agents": ["security-analyst"],
                    "strategy": "parallel",
                    "max_tokens": 8192,
                }

        orch = CortexOrchestrator(agent_router=MockRouter())
        plan = orch._plan(_make_request(), ContextPacket())
        assert plan["agents"] == ["security-analyst"]


# ── Execution (stub mode) ───────────────────────────────────────────────


class TestExecution:
    def test_no_executor_single_agent(self):
        orch = CortexOrchestrator()
        result = orch._execute(
            _make_request(),
            ContextPacket(),
            {"agents": ["general"]},
        )
        assert result["agent_id"] == "general"
        assert result["status"] == "executed"

    def test_no_executor_multi_agent(self):
        orch = CortexOrchestrator()
        result = orch._execute(
            _make_request(),
            ContextPacket(),
            {"agents": ["general", "researcher"]},
        )
        assert result["multi_agent"] is True
        assert len(result["results"]) == 2

    def test_budget_exceeded_raises(self):
        class MockBudget:
            def get_mission_budget(self, mission_id):
                class State:
                    total_cost_usd = 5.0

                return State()

        orch = CortexOrchestrator(budget_manager=MockBudget())
        with pytest.raises(BudgetExhaustedError):
            orch._execute(
                _make_request(budget_limit_usd=1.0),
                ContextPacket(),
                {"agents": ["general"]},
            )

    def test_budget_ok_does_not_raise(self):
        class MockBudget:
            def get_mission_budget(self, mission_id):
                class State:
                    total_cost_usd = 0.01

                return State()

        orch = CortexOrchestrator(budget_manager=MockBudget())
        result = orch._execute(
            _make_request(budget_limit_usd=1.0),
            ContextPacket(),
            {"agents": ["general"]},
        )
        assert result["status"] == "executed"


# ── Persistence ──────────────────────────────────────────────────────────


class TestPersistence:
    def test_returns_sha256_hash(self):
        orch = CortexOrchestrator()
        output = {"content": "test output"}
        result_hash = orch._persist(_make_request(), output)
        # Verify deterministic hash
        expected = hashlib.sha256(
            json.dumps(output, sort_keys=True, default=str).encode()
        ).hexdigest()
        assert result_hash == expected

    def test_same_output_same_hash(self):
        orch = CortexOrchestrator()
        output = {"key": "value", "nested": [1, 2, 3]}
        h1 = orch._persist(_make_request(), output)
        h2 = orch._persist(_make_request(), output)
        assert h1 == h2

    def test_ledger_append_called(self):
        class MockLedger:
            def __init__(self):
                self.calls = []

            def append(self, **kwargs):
                self.calls.append(kwargs)

        ledger = MockLedger()
        orch = CortexOrchestrator(ledger=ledger)
        orch._persist(_make_request(mission_id="m-42"), {"data": True})
        assert len(ledger.calls) == 1
        assert ledger.calls[0]["mission_id"] == "m-42"

    def test_ledger_failure_does_not_raise(self):
        class BrokenLedger:
            def append(self, **kwargs):
                raise ConnectionError("DB down")

        orch = CortexOrchestrator(ledger=BrokenLedger())
        # Should not raise - error is logged, hash still returned
        result = orch._persist(_make_request(), {"data": True})
        assert len(result) == 64  # SHA-256 hex


# ── Delivery ─────────────────────────────────────────────────────────────


class TestDelivery:
    def test_no_delivery_manager_ok(self):
        orch = CortexOrchestrator(delivery_manager=None)
        # Should not raise
        orch._deliver(_make_request(), {"result": "test"})

    def test_delivery_called(self):
        class MockDelivery:
            def __init__(self):
                self.delivered = []

            def deliver(self, output, target, mission_id):
                self.delivered.append((output, mission_id))

        dm = MockDelivery()
        orch = CortexOrchestrator(delivery_manager=dm)
        orch._deliver(_make_request(mission_id="m-99"), {"result": "test"})
        assert len(dm.delivered) == 1
        assert dm.delivered[0][1] == "m-99"


# ── Full Sync Pipeline ──────────────────────────────────────────────────


class TestFullPipeline:
    def test_success_flow(self):
        orch = CortexOrchestrator()
        result = orch.run(_make_request())
        assert result.status == PipelineStatus.SUCCESS
        assert result.mission_id == "m-test-001"
        assert result.ledger_hash != ""
        assert len(result.stages) == 6
        assert result.latency_ms > 0

    def test_budget_exhausted_flow(self):
        class MockBudget:
            def get_mission_budget(self, mission_id):
                class State:
                    total_cost_usd = 100.0

                return State()

        orch = CortexOrchestrator(budget_manager=MockBudget())
        result = orch.run(_make_request(budget_limit_usd=0.10))
        assert result.status == PipelineStatus.BUDGET_EXHAUSTED
        assert "already at" in result.error

    def test_all_stages_traced(self):
        orch = CortexOrchestrator()
        result = orch.run(_make_request())
        stage_names = [s.stage for s in result.stages]
        expected = [
            PipelineStage.INGRESS,
            PipelineStage.CONTEXT,
            PipelineStage.PLANNING,
            PipelineStage.EXECUTION,
            PipelineStage.PERSISTENCE,
            PipelineStage.EGRESS,
        ]
        assert stage_names == expected


# ── Data Model Tests ─────────────────────────────────────────────────────


class TestStageTrace:
    def test_latency_auto_calculated(self):
        t = StageTrace(
            stage=PipelineStage.INGRESS,
            started_at=1000.0,
            ended_at=1000.5,
        )
        assert t.latency_ms == pytest.approx(500.0)

    def test_explicit_latency_preserved(self):
        t = StageTrace(
            stage=PipelineStage.INGRESS,
            started_at=1000.0,
            ended_at=1000.5,
            latency_ms=999.0,
        )
        assert t.latency_ms == 999.0


class TestPipelineResult:
    def test_latency_from_completed_at(self):
        r = PipelineResult(
            mission_id="m-1",
            status=PipelineStatus.SUCCESS,
            created_at=1000.0,
            completed_at=1002.0,
        )
        assert r.latency_ms == pytest.approx(2000.0)

    def test_latency_fallback_to_stages(self):
        r = PipelineResult(
            mission_id="m-1",
            status=PipelineStatus.SUCCESS,
            stages=[
                StageTrace(
                    stage=PipelineStage.INGRESS,
                    started_at=0,
                    ended_at=0,
                    latency_ms=100.0,
                ),
                StageTrace(
                    stage=PipelineStage.CONTEXT,
                    started_at=0,
                    ended_at=0,
                    latency_ms=200.0,
                ),
            ],
        )
        assert r.latency_ms == pytest.approx(300.0)

    def test_total_tokens(self):
        r = PipelineResult(
            mission_id="m-1",
            status=PipelineStatus.SUCCESS,
            stages=[
                StageTrace(
                    stage=PipelineStage.EXECUTION,
                    started_at=0,
                    ended_at=0,
                    tokens_in=100,
                    tokens_out=200,
                ),
            ],
        )
        assert r.total_tokens == 300
