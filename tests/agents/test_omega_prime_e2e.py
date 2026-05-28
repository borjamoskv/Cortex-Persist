import asyncio

import pytest

from cortex.agents.base import BaseAgent
from cortex.agents.builtins.omega_prime import OmegaPrimeAgent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind


class InMemoryMessageBus:
    def __init__(self):
        self.messages = []
        self.subscribers = {}

    async def send(self, message: AgentMessage) -> None:
        self.messages.append(message)
        if message.recipient in self.subscribers:
            await self.subscribers[message.recipient](message)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        raise NotImplementedError("Use subscribe for this fake bus")

    async def broadcast(self, message: AgentMessage) -> None:
        for subscriber in self.subscribers.values():
            await subscriber(message)

    def subscribe(self, agent_id: str, handler):
        self.subscribers[agent_id] = handler

    async def shutdown(self):
        pass


class FakeToolExecutor:
    def __init__(self, responses):
        self.responses = responses

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        return self.responses


class SpyAgent(BaseAgent):
    def __init__(self, manifest: AgentManifest, bus):
        super().__init__(manifest=manifest, bus=bus)
        self.received_messages = []

    async def handle_message(self, message: AgentMessage) -> None:
        self.received_messages.append(message)

    def has_message_type(self, mtype: MessageKind) -> bool:
        return any(m.kind == mtype for m in self.received_messages)


class FakeVerificationAgent(BaseAgent):
    def __init__(self, bus):
        manifest = AgentManifest(agent_id="verification-agent", purpose="test")
        super().__init__(manifest=manifest, bus=bus)

    async def handle_message(self, message: AgentMessage) -> None:
        if message.kind == MessageKind.VERIFICATION_REQUEST:
            await self.bus.send(
                AgentMessage(
                    correlation_id=message.correlation_id,
                    causation_id=message.message_id,
                    sender=self.agent_id,
                    recipient=message.sender,
                    kind=MessageKind.VERIFICATION_RESULT,
                    payload={
                        "ok": True,
                        "verdict": "accepted",
                        "reasons": [],
                        "candidate": message.payload["candidate"],
                    },
                )
            )


async def eventually_assert(condition, timeout=1.0, interval=0.05):
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        if condition():
            return
        await asyncio.sleep(interval)
    assert condition(), "Condition not met within timeout"


@pytest.mark.asyncio
async def test_omega_prime_executes_tool_and_completes_task():
    bus = InMemoryMessageBus()
    tool_executor = FakeToolExecutor({"answer": 42})

    req_manifest = AgentManifest(agent_id="requester", purpose="test")
    requester = SpyAgent(manifest=req_manifest, bus=bus)

    verifier = FakeVerificationAgent(bus=bus)

    omega_manifest = AgentManifest(agent_id="omega-prime", purpose="test")
    omega = OmegaPrimeAgent(
        manifest=omega_manifest,
        bus=bus,
        tool_executor=tool_executor,
    )

    # We wire up the fake bus manually for testing
    bus.subscribe(requester.agent_id, requester.handle_message)
    bus.subscribe(omega.agent_id, omega.handle_message)
    bus.subscribe(verifier.agent_id, verifier.handle_message)

    msg = AgentMessage(
        correlation_id="corr-1",
        sender="requester",
        recipient="omega-prime",
        kind=MessageKind.TASK_REQUEST,
        payload={
            "task_id": "task-1",
            "objective": "tool:calculator",
            "input": {"expression": "40+2"},
            "constraints": {},
        },
    )

    await bus.send(msg)

    await eventually_assert(lambda: requester.has_message_type(MessageKind.TASK_COMPLETED))

    completed_msg = next(
        m for m in requester.received_messages if m.kind == MessageKind.TASK_COMPLETED
    )
    assert completed_msg.payload["task_id"] == "task-1"
    assert completed_msg.payload["output"] == {"answer": 42}
