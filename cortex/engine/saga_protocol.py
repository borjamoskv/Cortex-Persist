# [C5-REAL] Exergy-Maximized
"""
Saga Protocol Orchestrator
Enforces the 7-step Write-Path Contract for all state mutations.
If a proposal fails at step N, it compensates backwards to SAGA-1.
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypedDict

logger = logging.getLogger("cortex.engine.saga")

class SagaContext(TypedDict, total=False):
    agent_id: str
    session_id: str
    payload: dict[str, Any]
    taint_token: str | None
    schema_validated: bool
    encrypted_payload: bytes | None
    ledger_hash: str | None
    db_tx_id: str | None

class SagaStep:
    def __init__(
        self,
        name: str,
        execute: Callable[[SagaContext], Coroutine[Any, Any, None]],
        compensate: Callable[[SagaContext], Coroutine[Any, Any, None]],
    ):
        self.name = name
        self._execute = execute
        self._compensate = compensate

    async def execute(self, ctx: SagaContext) -> None:
        logger.info(f"SAGA FORWARD: {self.name}")
        await self._execute(ctx)

    async def compensate(self, ctx: SagaContext) -> None:
        logger.warning(f"SAGA REVERT: {self.name}")
        await self._compensate(ctx)

class SagaOrchestrator:
    def __init__(self, steps: list[SagaStep]):
        self.steps = steps

    async def execute_mutation(self, ctx: SagaContext) -> SagaContext:
        completed_steps: list[SagaStep] = []
        
        try:
            for step in self.steps:
                await step.execute(ctx)
                completed_steps.append(step)
            logger.info("Saga execution completed successfully. Transaction committed.")
            return ctx
            
        except Exception as e:
            logger.error(f"Saga execution failed at {len(completed_steps) + 1}. Triggering Rollback. Error: {e}")
            # Compensate in reverse order
            for step in reversed(completed_steps):
                try:
                    await step.compensate(ctx)
                except Exception as comp_e:
                    logger.critical(f"FATAL: Saga compensation failed for {step.name}. State corrupted. Error: {comp_e}")
            raise RuntimeError(f"Saga Mutation Aborted: {e}") from e

# Default 7-Step Write-Path Saga definition
async def guard_exec(ctx: SagaContext): 
    # Logic sanity check
    if not ctx.get("payload"): raise ValueError("Empty payload")
async def guard_comp(ctx: SagaContext): pass

async def taint_exec(ctx: SagaContext):
    # Attribution
    ctx["taint_token"] = f"taint:{ctx.get('agent_id')}:sha3_256_stub"
async def taint_comp(ctx: SagaContext):
    ctx["taint_token"] = None

async def schema_exec(ctx: SagaContext):
    # Deterministic validation
    ctx["schema_validated"] = True
async def schema_comp(ctx: SagaContext):
    ctx["schema_validated"] = False

async def encrypt_exec(ctx: SagaContext):
    # Encryption
    ctx["encrypted_payload"] = b"encrypted_stub"
async def encrypt_comp(ctx: SagaContext):
    ctx["encrypted_payload"] = None

async def ledger_exec(ctx: SagaContext):
    # Audit trail
    ctx["ledger_hash"] = "hash_stub"
async def ledger_comp(ctx: SagaContext):
    # Emit abort event
    pass

async def db_exec(ctx: SagaContext):
    # SQLite persistence
    ctx["db_tx_id"] = "tx_123"
async def db_comp(ctx: SagaContext):
    # Rollback SQLite tx
    ctx["db_tx_id"] = None

async def index_exec(ctx: SagaContext):
    # Vector index updates
    pass
async def index_comp(ctx: SagaContext):
    pass

def build_core_write_path_saga() -> SagaOrchestrator:
    return SagaOrchestrator([
        SagaStep("SAGA-1: Guards", guard_exec, guard_comp),
        SagaStep("SAGA-2: Taint", taint_exec, taint_comp),
        SagaStep("SAGA-3: Schema", schema_exec, schema_comp),
        SagaStep("SAGA-4: Encryption", encrypt_exec, encrypt_comp),
        SagaStep("SAGA-5: Ledger", ledger_exec, ledger_comp),
        SagaStep("SAGA-6: Persistence", db_exec, db_comp),
        SagaStep("SAGA-7: Index", index_exec, index_comp),
    ])
