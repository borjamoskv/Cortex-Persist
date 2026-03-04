"""Tests for VEX — Verifiable Execution.

Covers models, planner, receipt verification, and the execution loop
with a mock executor.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cortex.vex.models import (
    ExecutionReceipt,
    PlannedStep,
    StepResult,
    TaskPlan,
    VEXStatus,
)
from cortex.vex.planner import Planner
from cortex.vex.receipt import export_receipt, load_receipt, verify_receipt

# ─── Model Tests ──────────────────────────────────────────────────


class TestPlannedStep:
    def test_content_hash_deterministic(self):
        step = PlannedStep(
            step_id="s1",
            description="Test step",
            tool="cortex_store",
            args={"project": "test", "content": "hello"},
        )
        h1 = step.content_hash()
        h2 = step.content_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256

    def test_different_steps_different_hashes(self):
        s1 = PlannedStep(step_id="s1", description="A", tool="cortex_store")
        s2 = PlannedStep(step_id="s2", description="B", tool="cortex_search")
        assert s1.content_hash() != s2.content_hash()

    def test_frozen_dataclass(self):
        step = PlannedStep(step_id="s1", description="Test", tool="t")
        with pytest.raises(AttributeError):
            step.step_id = "s2"  # type: ignore[misc]


class TestTaskPlan:
    def test_plan_hash_deterministic(self):
        plan = TaskPlan(
            task_id="vex_test_123",
            intent="Test intent",
            steps=[
                PlannedStep(step_id="s1", description="A", tool="t1"),
                PlannedStep(step_id="s2", description="B", tool="t2"),
            ],
        )
        h1 = plan.plan_hash
        h2 = plan.plan_hash
        assert h1 == h2
        assert len(h1) == 64

    def test_plan_hash_changes_with_steps(self):
        plan1 = TaskPlan(
            task_id="vex_test",
            intent="Same intent",
            steps=[PlannedStep(step_id="s1", description="A", tool="t1")],
        )
        plan2 = TaskPlan(
            task_id="vex_test",
            intent="Same intent",
            steps=[PlannedStep(step_id="s1", description="B", tool="t1")],
        )
        assert plan1.plan_hash != plan2.plan_hash

    def test_to_dict(self):
        plan = TaskPlan(
            task_id="vex_t",
            intent="Test",
            steps=[PlannedStep(step_id="s1", description="D", tool="t")],
        )
        d = plan.to_dict()
        assert d["task_id"] == "vex_t"
        assert d["intent"] == "Test"
        assert len(d["steps"]) == 1
        assert "plan_hash" in d
        assert "content_hash" in d["steps"][0]


class TestStepResult:
    def test_content_hash(self):
        r = StepResult(step_id="s1", success=True, output="Done")
        h = r.content_hash()
        assert len(h) == 64

    def test_hash_changes_on_failure(self):
        r1 = StepResult(step_id="s1", success=True, output="Done")
        r2 = StepResult(step_id="s1", success=False, output="Done", error="oops")
        assert r1.content_hash() != r2.content_hash()

    def test_to_dict(self):
        r = StepResult(
            step_id="s1",
            success=True,
            output="Result output",
            duration_ms=42,
            tx_hash="abc123",
        )
        d = r.to_dict()
        assert d["step_id"] == "s1"
        assert d["success"] is True
        assert d["duration_ms"] == 42
        assert "content_hash" in d


class TestExecutionReceipt:
    def _make_receipt(self) -> ExecutionReceipt:
        return ExecutionReceipt(
            task_id="vex_test_001",
            plan_hash="abc123def456",
            intent="Test execution",
            status=VEXStatus.COMPLETED,
            steps=[
                StepResult(step_id="s1", success=True, output="OK", duration_ms=10),
                StepResult(step_id="s2", success=True, output="OK", duration_ms=20),
            ],
            total_duration_ms=30,
        )

    def test_receipt_hash_deterministic(self):
        r = self._make_receipt()
        h1 = r.receipt_hash
        h2 = r.receipt_hash
        assert h1 == h2
        assert len(h1) == 64

    def test_receipt_hash_changes_on_mutation(self):
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        r2.steps.append(StepResult(step_id="s3", success=False, error="boom"))
        assert r1.receipt_hash != r2.receipt_hash

    def test_verify(self):
        r = self._make_receipt()
        assert r.verify() is True

    def test_verify_fails_without_plan_hash(self):
        r = self._make_receipt()
        r.plan_hash = ""
        assert r.verify() is False

    def test_abort(self):
        r = ExecutionReceipt(task_id="vex_t", plan_hash="h")
        r.abort(reason="tether_violation", step_id="s1")
        assert r.status == VEXStatus.ABORTED
        assert len(r.steps) == 1
        assert r.steps[0].error == "tether_violation"

    def test_add_step(self):
        r = ExecutionReceipt(task_id="vex_t", plan_hash="h")
        r.add_step(StepResult(step_id="s1", success=True, duration_ms=50))
        assert len(r.steps) == 1
        assert r.total_duration_ms == 50

    def test_to_dict(self):
        r = self._make_receipt()
        d = r.to_dict()
        assert d["vex_version"] == "1.0"
        assert d["task_id"] == "vex_test_001"
        assert d["status"] == "completed"
        assert len(d["steps"]) == 2
        assert "receipt_hash" in d

    def test_export_proof(self):
        r = self._make_receipt()
        proof = r.export_proof()
        data = json.loads(proof)
        assert data["task_id"] == "vex_test_001"
        assert "receipt_hash" in data

    def test_from_dict_roundtrip(self):
        r1 = self._make_receipt()
        d = r1.to_dict()
        r2 = ExecutionReceipt.from_dict(d)
        assert r2.task_id == r1.task_id
        assert r2.plan_hash == r1.plan_hash
        assert r2.status == r1.status
        assert len(r2.steps) == len(r1.steps)
        assert r2.receipt_hash == r1.receipt_hash


# ─── Planner Tests ────────────────────────────────────────────────


class TestPlanner:
    @pytest.mark.asyncio
    async def test_deterministic_plan(self):
        planner = Planner()
        plan = await planner.plan("Fix the auth module")
        assert plan.task_id.startswith("vex_")
        assert len(plan.steps) >= 1
        assert plan.plan_hash
        assert plan.intent == "Fix the auth module"

    @pytest.mark.asyncio
    async def test_plan_with_custom_backend(self):
        class MockBackend:
            async def decompose(self, intent, context=None):
                return [
                    {
                        "step_id": "s1",
                        "description": "Read file",
                        "tool": "file_read",
                        "args": {"path": "/tmp/t"},
                    },
                    {
                        "step_id": "s2",
                        "description": "Store result",
                        "tool": "cortex_store",
                        "args": {"project": "test"},
                    },
                ]

        planner = Planner(backend=MockBackend(), model="test-model")
        plan = await planner.plan("Do something")
        assert len(plan.steps) == 2
        assert plan.steps[0].tool == "file_read"
        assert plan.steps[1].tool == "cortex_store"
        assert plan.model == "test-model"


# ─── Receipt Verification Tests ───────────────────────────────────


class TestReceiptVerification:
    def test_verify_valid_receipt(self):
        r = ExecutionReceipt(
            task_id="vex_v001",
            plan_hash="test_plan_hash",
            intent="Test",
            status=VEXStatus.COMPLETED,
            steps=[
                StepResult(step_id="s1", success=True, output="OK"),
            ],
        )
        report = verify_receipt(r)
        assert report["valid"] is True
        assert report["violations"] == []
        assert report["steps_verified"] == 1

    def test_verify_missing_plan_hash(self):
        r = ExecutionReceipt(task_id="vex_v002", plan_hash="", status=VEXStatus.COMPLETED)
        report = verify_receipt(r)
        assert report["valid"] is False
        assert any("plan_hash" in v for v in report["violations"])

    def test_verify_duplicate_step_ids(self):
        r = ExecutionReceipt(
            task_id="vex_v003",
            plan_hash="h",
            steps=[
                StepResult(step_id="s1", success=True),
                StepResult(step_id="s1", success=False),  # duplicate
            ],
        )
        report = verify_receipt(r)
        assert report["valid"] is False
        assert any("Duplicate" in v for v in report["violations"])


class TestReceiptExportLoad:
    def test_export_and_load(self):
        r = ExecutionReceipt(
            task_id="vex_el001",
            plan_hash="export_test_hash",
            intent="Export test",
            status=VEXStatus.COMPLETED,
            steps=[
                StepResult(step_id="s1", success=True, output="Hello", duration_ms=10),
            ],
            total_duration_ms=10,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "receipt.json"
            meta = export_receipt(r, path)

            assert meta["task_id"] == "vex_el001"
            assert meta["file_hash"]
            assert path.exists()

            # Load and verify roundtrip
            loaded = load_receipt(path)
            assert loaded.task_id == r.task_id
            assert loaded.plan_hash == r.plan_hash
            assert loaded.receipt_hash == r.receipt_hash
            assert len(loaded.steps) == 1

            # Verify the loaded receipt
            report = verify_receipt(loaded)
            assert report["valid"] is True
