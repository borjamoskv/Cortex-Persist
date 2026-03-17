from __future__ import annotations

from typing import Protocol

from cortex.agents.base import BaseAgent
from cortex.agents.contracts import (
    TaskCompletedPayload,
    TaskFailedPayload,
    TaskRequestPayload,
    ToolCallPayload,
    ToolResultPayload,
    VerificationRequestPayload,
    VerificationResultPayload,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind


class ToolExecutor(Protocol):
    async def execute(self, tool_name: str, arguments: dict) -> dict: ...


class OmegaPrimeAgent(BaseAgent):
    def __init__(
        self,
        *,
        manifest: AgentManifest,
        bus,
        tool_registry=None,
        tool_executor: ToolExecutor,
        verification_agent_id: str = "verification-agent",
        handoff_agent_id: str = "handoff-agent",
    ) -> None:
        super().__init__(manifest=manifest, bus=bus, tool_registry=tool_registry)
        self._tool_executor = tool_executor
        self._verification_agent_id = verification_agent_id
        self._handoff_agent_id = handoff_agent_id

    async def handle_message(self, message: AgentMessage) -> None:
        if message.kind == MessageKind.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.kind == MessageKind.VERIFICATION_RESULT:
            await self._handle_verification_result(message)

    async def _handle_task_request(self, message: AgentMessage) -> None:
        try:
            task = TaskRequestPayload.model_validate(message.payload)
        except ValueError as e:
            await self._fail_initial(message, f"Invalid payload: {e}")
            return

        await self.bus.send(
            AgentMessage(
                correlation_id=message.correlation_id,
                causation_id=message.message_id,
                sender=self.agent_id,
                recipient=message.sender,
                kind=MessageKind.TASK_ACCEPTED,
                payload={"task_id": task.task_id},
            )
        )

        try:
            plan = self._plan(task)

            if plan["mode"] == "direct":
                await self._complete_task(
                    message,
                    task,
                    output=plan["output"],
                )
                return

            if plan["mode"] == "tool":
                tool_payload = ToolCallPayload(
                    tool_name=plan["tool_name"],
                    arguments=plan["arguments"],
                )

                tool_result_raw = await self._tool_executor.execute(
                    tool_payload.tool_name,
                    tool_payload.arguments,
                )

                tool_result = ToolResultPayload(
                    tool_name=tool_payload.tool_name,
                    ok=True,
                    result=tool_result_raw,
                )

                # Store context for asynchronous verification
                self.memory.scratchpad[message.correlation_id] = {
                    "original_message": message,
                    "task": task,
                    "tool_result": tool_result,
                }

                verification_request = AgentMessage(
                    correlation_id=message.correlation_id,
                    causation_id=message.message_id,
                    sender=self.agent_id,
                    recipient=self._verification_agent_id,
                    kind=MessageKind.VERIFICATION_REQUEST,
                    payload=VerificationRequestPayload(
                        subject="tool_result",
                        candidate=tool_result.model_dump(),
                    ).model_dump(),
                )

                await self.bus.send(verification_request)
                return

            await self._request_handoff(message, task, reason="unsupported_plan_mode")

        except Exception as exc:
            await self._fail_task(
                message,
                task,
                error=f"{type(exc).__name__}: {exc}",
                retryable=False,
            )

    async def _handle_verification_result(self, message: AgentMessage) -> None:
        ctx = self.memory.scratchpad.pop(message.correlation_id, None)
        if not ctx:
            self.state.record_error(f"No context for correlation_id {message.correlation_id}")
            return

        original_message: AgentMessage = ctx["original_message"]
        task: TaskRequestPayload = ctx["task"]
        tool_result: ToolResultPayload = ctx["tool_result"]

        try:
            verdict = VerificationResultPayload.model_validate(message.payload)

            if verdict.verdict == "accepted":
                await self._complete_task(
                    original_message,
                    task,
                    output=tool_result.result,
                )
                return

            if verdict.verdict == "needs_handoff":
                await self._request_handoff(original_message, task, reason="verification_uncertain")
                return

            await self._fail_task(
                original_message,
                task,
                error="Verification rejected tool result",
                retryable=False,
            )
        except Exception as exc:
            await self._fail_task(
                original_message,
                task,
                error=f"Verification result handling failed: {exc}",
                retryable=False,
            )


    def _plan(self, task: TaskRequestPayload) -> dict:
        objective = task.objective.lower()

        if objective.startswith("echo:"):
            return {
                "mode": "direct",
                "output": {"text": objective.removeprefix("echo:").strip()},
            }

        if "tool:" in objective:
            _, tool_name = objective.split("tool:", 1)
            return {
                "mode": "tool",
                "tool_name": tool_name.strip(),
                "arguments": task.input,
            }

        return {"mode": "handoff"}

    async def _request_handoff(
        self,
        original: AgentMessage,
        task: TaskRequestPayload,
        *,
        reason: str,
    ) -> None:
        await self.bus.send(
            AgentMessage(
                correlation_id=original.correlation_id,
                causation_id=original.message_id,
                sender=self.agent_id,
                recipient=self._handoff_agent_id,
                kind=MessageKind.HANDOFF_REQUEST,
                payload={
                    "task_id": task.task_id,
                    "reason": reason,
                    "objective": task.objective,
                    "input": task.input,
                },
            )
        )

    async def _complete_task(
        self,
        original: AgentMessage,
        task: TaskRequestPayload,
        *,
        output: dict,
    ) -> None:
        await self.bus.send(
            AgentMessage(
                correlation_id=original.correlation_id,
                causation_id=original.message_id,
                sender=self.agent_id,
                recipient=original.sender,
                kind=MessageKind.TASK_COMPLETED,
                payload=TaskCompletedPayload(
                    task_id=task.task_id,
                    output=output,
                ).model_dump(),
            )
        )

    async def _fail_task(
        self,
        original: AgentMessage,
        task: TaskRequestPayload,
        *,
        error: str,
        retryable: bool,
    ) -> None:
        await self.bus.send(
            AgentMessage(
                correlation_id=original.correlation_id,
                causation_id=original.message_id,
                sender=self.agent_id,
                recipient=original.sender,
                kind=MessageKind.TASK_FAILED,
                payload=TaskFailedPayload(
                    task_id=task.task_id,
                    error=error,
                    retryable=retryable,
                ).model_dump(),
            )
        )

    async def _fail_initial(self, original: AgentMessage, error: str) -> None:
        await self.bus.send(
            AgentMessage(
                correlation_id=original.correlation_id,
                causation_id=original.message_id,
                sender=self.agent_id,
                recipient=original.sender,
                kind=MessageKind.TASK_FAILED,
                payload={"error": error},
            )
        )
