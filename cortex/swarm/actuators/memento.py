"""Memento Actuator — Bridges MementoAgent into SwarmFactory protocol.

Adapts the sovereign Memento specialist (episodic→semantic crystallization)
into the ActuatorProtocol interface so it can be recruited by SwarmFactory
alongside skill- and LLM-based agents.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse

logger = logging.getLogger("cortex.swarm.actuators.memento")


class MementoActuator(ActuatorProtocol):
    """Sovereign Memento Actuator (Ω₁₃ — Cognitive Thermodynamics).

    Wraps MementoAgent to conform to the swarm ActuatorProtocol.
    Routes tasks to the appropriate Memento lifecycle method.
    """

    def __init__(self, engine: Any = None) -> None:
        self._engine = engine
        self._agent: Any | None = None
        self._provider_id = "specialist:memento:v1"

    async def _ensure_agent(self) -> Any:
        """Lazy-init MementoAgent on first use."""
        if self._agent is None:
            from cortex.agents.memento import MementoAgent

            self._agent = MementoAgent(engine=self._engine)
            await self._agent.initialize()
            logger.info("MementoActuator: Agent initialized")
        return self._agent

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        task_id: str | None = None,
    ) -> ActuatorResponse:
        """Route task to the appropriate Memento operation."""
        agent = await self._ensure_agent()
        operation = context.get("operation", "tick")

        if operation == "record_trace":
            action = context.get("action", task)
            observation = context.get("observation", "")
            await agent.record_trace(action, observation)
            return ActuatorResponse(
                content=f"Trace recorded: {action[:50]}",
                metadata={"operation": "record_trace", "session": agent.session_id},
            )

        if operation == "recall":
            query = context.get("query", task)
            limit = context.get("limit", 5)
            results = await agent.recall(query, limit=limit)
            return ActuatorResponse(
                content=f"Recalled {len(results)} facts",
                metadata={"operation": "recall", "results": results},
            )

        if operation == "compact":
            await agent.compact()
            return ActuatorResponse(
                content="Shannon compaction complete",
                metadata={"operation": "compact"},
            )

        if operation == "maintenance":
            await agent.run_maintenance()
            return ActuatorResponse(
                content="Thermodynamic maintenance complete",
                metadata={"operation": "maintenance"},
            )

        # Default: tick (consolidation cycle)
        await agent.tick()
        return ActuatorResponse(
            content=f"Memento tick complete (stage: {agent.stage.value})",
            metadata={
                "operation": "tick",
                "stage": agent.stage.value,
                "session": agent.session_id,
            },
        )

    async def health_check(self) -> bool:
        """Verify Memento agent is operational."""
        try:
            agent = await self._ensure_agent()
            return agent._initialized
        except Exception:
            return False

    @property
    def provider_id(self) -> str:
        return self._provider_id
