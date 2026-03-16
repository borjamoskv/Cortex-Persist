"""VEX Execution Loop — Hash-chained verified execution.

This is the core of VEX: executes each step in a TaskPlan and produces
a cryptographic ExecutionReceipt with hash-chained transaction records.

Every step:
1. Tether check (safety boundary)
2. Execute tool
3. Record transaction in hash-chained ledger
4. Persist result as CORTEX fact
5. Append to receipt

Derivation: Ω₃ (Byzantine Default) — nothing is trusted, everything is verified.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from cortex.vex.models import (
    ExecutionReceipt,
    PlannedStep,
    StepResult,
    TaskPlan,
    VEXStatus,
    _now_iso,
    _sha256,
)

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["VEXRunner"]

logger = logging.getLogger("cortex.vex")


# Type alias for tool executor functions.
ToolExecutor = Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class VEXRunner:
    """Verified Execution Runner.

    Executes a TaskPlan step-by-step with full cryptographic verification.
    Each step produces a transaction in the CORTEX ledger and a StepResult
    in the ExecutionReceipt.

    Args:
        engine: CortexEngine instance for memory + ledger operations.
        tool_executor: Async function that executes a tool by name with args.
                       Signature: async (tool_name: str, args: dict) -> dict
                       Must return {"success": bool, "output": str, ...}
        max_step_retries: Max retries per step (default: 0 = no retries).
        tether_checks: Whether to enforce tether boundary checks.
    """

    def __init__(
        self,
        engine: CortexEngine,
        tool_executor: ToolExecutor | None = None,
        max_step_retries: int = 0,
        tether_checks: bool = True,
    ) -> None:
        self._engine = engine
        self._executor = tool_executor or self._default_executor
        self._max_retries = max_step_retries
        self._tether_checks = tether_checks

    async def execute(self, plan: TaskPlan) -> ExecutionReceipt:
        """Execute a TaskPlan and return a verified ExecutionReceipt.

        This is the main entry point. It runs the full VEX loop:
        plan → execute steps → record transactions → generate receipt.
        """
        receipt = ExecutionReceipt(
            task_id=plan.task_id,
            plan_hash=plan.plan_hash,
            intent=plan.intent,
            status=VEXStatus.RUNNING,
            model=plan.model,
            source=plan.source,
        )

        # Record the plan itself as a transaction.
        await self._record_plan_transaction(plan)

        logger.info(
            "VEX execution started: task_id=%s steps=%d",
            plan.task_id,
            len(plan.steps),
        )

        all_succeeded = True

        for step in plan.steps:
            # 1. TETHER CHECK
            if self._tether_checks and step.tether_check:
                violation = await self._check_tether(step)
                if violation:
                    receipt.abort(
                        reason=f"tether_violation: {violation}",
                        step_id=step.step_id,
                    )
                    logger.warning(
                        "VEX tether violation: task=%s step=%s reason=%s",
                        plan.task_id,
                        step.step_id,
                        violation,
                    )
                    all_succeeded = False
                    break

            # 2. EXECUTE STEP
            result = await self._execute_step(step, plan.task_id)
            receipt.add_step(result)

            if not result.success:
                all_succeeded = False
                logger.warning(
                    "VEX step failed: task=%s step=%s error=%s",
                    plan.task_id,
                    step.step_id,
                    result.error,
                )
                # Don't break — continue to record remaining steps as skipped
                # unless it's critical. For now, we stop on first failure.
                break

        # 3. FINALIZE
        if receipt.status != VEXStatus.ABORTED:
            receipt.status = VEXStatus.COMPLETED if all_succeeded else VEXStatus.PARTIAL
        receipt.completed_at = _now_iso()

        # 4. MERKLE CHECKPOINT
        receipt.merkle_root = await self._create_checkpoint(plan.task_id)

        # 5. RECORD RECEIPT as a fact
        await self._persist_receipt(receipt)

        logger.info(
            "VEX execution %s: task_id=%s steps=%d/%d duration=%dms receipt=%s",
            receipt.status.value,
            plan.task_id,
            sum(1 for s in receipt.steps if s.success),
            len(receipt.steps),
            receipt.total_duration_ms,
            receipt.receipt_hash[:16],
        )

        return receipt

    async def _execute_step(self, step: PlannedStep, task_id: str) -> StepResult:
        """Execute a single step with timing and error handling."""
        started_at = _now_iso()
        t0 = time.monotonic()

        try:
            result_data = await asyncio.wait_for(
                self._executor(step.tool, step.args),
                timeout=step.timeout_seconds,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            success = result_data.get("success", True)
            output = str(result_data.get("output", ""))
            error = result_data.get("error") if not success else None

        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            success = False
            output = ""
            error = f"Timeout after {step.timeout_seconds}s"

        except Exception as exc:  # noqa: BLE001 — VEX step catch-all boundary
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            success = False
            output = ""
            error = f"{type(exc).__name__}: {exc}"

        completed_at = _now_iso()

        # Record in the hash-chained ledger.
        tx_hash = await self._record_step_transaction(
            task_id, step, success, output, error, elapsed_ms
        )

        # Persist as CORTEX fact.
        fact_id = await self._persist_step_fact(task_id, step, success, output, tx_hash)

        return StepResult(
            step_id=step.step_id,
            success=success,
            output=output[:2000],  # Cap output for storage
            error=error,
            duration_ms=elapsed_ms,
            started_at=started_at,
            completed_at=completed_at,
            tx_hash=tx_hash,
            fact_id=fact_id,
        )

    # ─── Ledger Integration ───────────────────────────────────────

    async def _record_plan_transaction(self, plan: TaskPlan) -> None:
        """Record the plan as the first transaction in the chain."""
        try:
            conn = await self._engine.get_conn()
            await conn.execute(
                """INSERT INTO transactions
                   (project, action, detail, prev_hash, hash, timestamp, tenant_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan.task_id,
                    "vex_plan",
                    str(plan.to_dict())[:4000],
                    "GENESIS",
                    plan.plan_hash,
                    _now_iso(),
                    "default",
                ),
            )
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 — VEX transaction logging fallback
            logger.error("Failed to record plan transaction: %s", exc)

    async def _record_step_transaction(
        self,
        task_id: str,
        step: PlannedStep,
        success: bool,
        output: str,
        error: str | None,
        duration_ms: int,
    ) -> str | None:
        """Record a step execution in the hash-chained ledger."""
        try:
            conn = await self._engine.get_conn()

            # Get prev hash for this task.
            cursor = await conn.execute(
                "SELECT hash FROM transactions WHERE project = ? ORDER BY id DESC LIMIT 1",
                (task_id,),
            )
            row = await cursor.fetchone()
            prev_hash = row[0] if row else "GENESIS"

            detail = {
                "step_id": step.step_id,
                "tool": step.tool,
                "success": success,
                "duration_ms": duration_ms,
                "output_hash": _sha256(output) if output else "",
                "error": error,
            }
            detail_str = str(detail)[:4000]

            action = f"vex_step:{step.step_id}"
            ts = _now_iso()
            tx_hash = _sha256(f"{prev_hash}:{task_id}:{action}:{detail_str}:{ts}")

            await conn.execute(
                """INSERT INTO transactions
                   (project, action, detail, prev_hash, hash, timestamp, tenant_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, action, detail_str, prev_hash, tx_hash, ts, "default"),
            )
            await conn.commit()
            return tx_hash

        except Exception as exc:  # noqa: BLE001 — VEX step logging fallback
            logger.error("Failed to record step transaction: %s", exc)
            return None

    async def _create_checkpoint(self, task_id: str) -> str | None:
        """Create a Merkle checkpoint for this task's transactions."""
        try:
            if self._engine._ledger:
                cp = await self._engine._ledger.create_checkpoint_async()
                if cp:
                    return str(cp)
        except Exception as exc:  # noqa: BLE001 — VEX merkle cp skip
            logger.debug("Merkle checkpoint skipped: %s", exc)
        return None

    # ─── Memory Integration ───────────────────────────────────────

    async def _persist_step_fact(
        self,
        task_id: str,
        step: PlannedStep,
        success: bool,
        output: str,
        tx_hash: str | None,
    ) -> int | None:
        """Persist step result as a CORTEX fact."""
        try:
            status_str = "✅" if success else "❌"
            content = (
                f"[VEX {status_str}] {step.description}\nTool: {step.tool}\nOutput: {output[:500]}"
            )
            fact_id = await self._engine.store(
                project=task_id,
                content=content,
                fact_type="execution_step",
                tags=["vex", step.tool],
                source="agent:vex",
                meta={"tx_hash": tx_hash, "step_id": step.step_id},
            )
            return fact_id
        except Exception as exc:  # noqa: BLE001 — VEX step fact persistence fallback
            logger.error("Failed to persist step fact: %s", exc)
            return None

    async def _persist_receipt(self, receipt: ExecutionReceipt) -> None:
        """Persist the final receipt as a CORTEX fact."""
        try:
            content = (
                f"[VEX Receipt] {receipt.intent}\n"
                f"Status: {receipt.status.value}\n"
                f"Steps: {sum(1 for s in receipt.steps if s.success)}/{len(receipt.steps)}\n"
                f"Duration: {receipt.total_duration_ms}ms\n"
                f"Receipt Hash: {receipt.receipt_hash[:32]}..."
            )
            await self._engine.store(
                project=receipt.task_id,
                content=content,
                fact_type="execution_receipt",
                tags=["vex", "receipt"],
                source="agent:vex",
                meta={
                    "receipt_hash": receipt.receipt_hash,
                    "merkle_root": receipt.merkle_root,
                    "plan_hash": receipt.plan_hash,
                },
            )
        except Exception as exc:  # noqa: BLE001 — VEX receipt persistence fallback
            logger.error("Failed to persist receipt: %s", exc)

    # ─── Tether Integration ───────────────────────────────────────

    async def _check_tether(self, step: PlannedStep) -> str | None:
        """Check if a step violates tether boundaries.

        Returns violation reason or None if allowed.
        """
        # Phase 1: basic tool allowlist check.
        # Phase 2: full tether.md parsing with path/budget/entropy checks.
        dangerous_tools = frozenset(("shell_exec", "file_write", "network_request"))

        if step.tool in dangerous_tools:
            # For now just log — full tether enforcement comes in Phase 2.
            logger.info(
                "VEX tether: tool %s requires elevated permissions",
                step.tool,
            )
        return None  # No violation in Phase 1

    # ─── Default Executor ─────────────────────────────────────────

    async def _default_executor(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Default tool executor: delegates to CORTEX engine operations."""
        if tool == "cortex_store":
            fact_id = await self._engine.store(**args)
            return {"success": True, "output": f"Stored fact #{fact_id}", "fact_id": fact_id}

        if tool == "cortex_search":
            results = await self._engine.search(**args)
            return {
                "success": True,
                "output": f"Found {len(results)} results",
                "results": [r.to_dict() for r in results],  # type: ignore[reportAttributeAccessIssue]
            }

        if tool == "cortex_recall":
            results = await self._engine.recall(**args)
            return {
                "success": True,
                "output": f"Recalled {len(results)} facts",
                "results": [r.to_dict() for r in results],  # type: ignore[reportAttributeAccessIssue]
            }

        if tool == "cortex_deprecate":
            await self._engine.deprecate(**args)
            return {"success": True, "output": "Fact deprecated"}

        return {
            "success": False,
            "output": "",
            "error": f"Unknown tool: {tool}",
        }
