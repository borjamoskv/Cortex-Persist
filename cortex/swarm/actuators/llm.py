from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse

logger = logging.getLogger("cortex.swarm.actuators.llm")


class LLMActuator(ActuatorProtocol):
    """
    Sovereign LLM Actuator.
    Wraps the CortexLLMRouter to provide reasoning capabilities to the swarm.
    """

    def __init__(
        self,
        router: CortexLLMRouter,
        model_id: str,
        intent: str = "generic",
        provider_name: str = "default",
    ) -> None:
        self.router = router
        self._model_id = model_id
        self._intent = intent
        self._provider_id = f"llm:{provider_name}:{model_id}"

    async def execute(
        self, task: str, context: dict[str, Any], task_id: str | None = None
    ) -> ActuatorResponse:
        """Execute a task via the LLM router."""
        logger.info("LLMActuator: Executing task %s with model %s", task_id or "anon", self._model_id)

        prompt = CortexPrompt(
            system_instruction=(
                f"You are a specialized Swarm Agent with the following intent: {self._intent}. "
                f"Context: {context.get('instructions', '')}"
            ),
            working_memory=[{"role": "user", "content": task}],
            intent=IntentProfile(name=self._intent),
            project=context.get("project", "swarm"),
        )

        # Use resilient routing for the task
        result = await self.router.execute_resilient(prompt)

        if result.is_ok():
            return ActuatorResponse(
                content=result.unwrap(),
                metadata={
                    "model": self._model_id,
                    "intent": self._intent,
                    "provider": self._provider_id,
                    "task_id": task_id,
                },
            )
        
        return ActuatorResponse(
            content="",
            metadata={"error": result.error},
            status="failure",
            error=result.error,
        )

    async def health_check(self) -> bool:
        """Verify the router/primary provider is alive."""
        # A simple health check could be a very small token request or checking router state
        return self.router.primary is not None

    @property
    def provider_id(self) -> str:
        return self._provider_id
