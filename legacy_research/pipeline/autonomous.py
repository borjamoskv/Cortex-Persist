# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - One-Shot Autonomous Session.

Bootstraps the CORTEX ecosystem, processes a single intent deterministically,
persists the outcome to the C5-REAL SQLite engine, and tears down gracefully.
"""

import asyncio
import logging
import uuid
from typing import Any

from legacy_research.context.assembler import ContextAssembler
from cortex.engine import CortexEngine
from legacy_research.pipeline import DeliveryTarget, PipelineRequest, PipelineResult
from legacy_research.pipeline.executor import AgentExecutor
from legacy_research.pipeline.orchestrator import CortexOrchestrator

logger = logging.getLogger("cortex.pipeline.autonomous")


async def execute_autonomous_mission(
    intent: str,
    tenant_id: str = "default_tenant",
    budget_limit_usd: float = 1.0,
    timeout_s: float = 300.0,
    delivery_mode: str = "memory",
) -> PipelineResult:
    """Execute a single autonomous mission from intent to persistence.

    This embodies the One-Shot pattern:
    1. Bootstrap Engine (SQLite persistent state)
    2. Assemble pipeline components and wire Engine
    3. Execute the E2E orchestrator natively via async
    4. Teardown gracefully (connection pool close)
    """
    mission_id = f"mission_{uuid.uuid4().hex[:8]}"

    logger.info("Initializing Autonomous Mission %s", mission_id)

    # 1. Bootstrap Engine
    engine = CortexEngine()
    await engine.initialize()  # pyright: ignore[reportAttributeAccessIssue]

    try:
        # 2. Wire Components
        # Currently we use minimal wiring. In a full system, router & delivery
        # managers would be initialized here as well.
        assembler = ContextAssembler()
        executor = AgentExecutor()

        orchestrator = CortexOrchestrator(
            context_assembler=assembler,
            agent_executor=executor,
            engine=engine,
        )

        # 3. Create Request
        request = PipelineRequest(
            mission_id=mission_id,
            intent=intent,
            tenant_id=tenant_id,
            budget_limit_usd=budget_limit_usd,
            timeout_s=timeout_s,
            delivery=DeliveryTarget(mode=delivery_mode),  # pyright: ignore[reportCallIssue]
        )

        # 4. Execute E2E flow
        logger.info("Executing E2E flow for mission %s...", mission_id)
        result = await orchestrator.run_async(request)

        if result.status.name == "SUCCESS":
            logger.info(
                "Mission %s completed successfully. Hash: %s", mission_id, result.ledger_hash
            )
        else:
            logger.error("Mission %s failed or was cancelled: %s", mission_id, result.error)

        return result

    finally:
        # 5. Teardown Engine
        logger.info("Tearing down CortexEngine for mission %s", mission_id)
        await engine.teardown()  # pyright: ignore[reportAttributeAccessIssue]


def run_autonomous_sync(intent: str, **kwargs: Any) -> PipelineResult:
    """Synchronous wrapper for the autonomous mission executor.

    Useful for CLI invocations or legacy synchronous boundaries.
    """
    return asyncio.run(execute_autonomous_mission(intent, **kwargs))
