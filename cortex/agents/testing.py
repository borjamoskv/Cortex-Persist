"""CORTEX Agent Runtime — Test Utilities.

Shared mocks and helpers for standalone agent operation and testing.
"""

from __future__ import annotations

import asyncio
from typing import Any

from cortex.agents.message_schema import AgentMessage, MessageKind


class MockBus:
    """Minimal message bus for standalone operation and testing.

    Implements the MessageBus protocol with no-op send/receive,
    allowing agents to run outside the full nursery/supervisor stack.
    """

    async def receive(self, agent_id: str, timeout: float = 1.0) -> Any:
        """Block for `timeout` seconds, always returning None."""
        await asyncio.sleep(min(timeout, 1.0))
        return None

    async def send(self, message: Any) -> None:
        """No-op send — messages are silently discarded."""


class InMemoryBus:
    """Full in-memory message bus for integration testing.

    Tracks all sent messages and allows inspection by recipient,
    kind, correlation_id, etc. Use this for tests that need to
    assert on message flow between agents.
    """

    def __init__(self) -> None:
        self._sent: list[AgentMessage] = []
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}

    @property
    def sent(self) -> list[AgentMessage]:
        """All messages sent through this bus."""
        return list(self._sent)

    async def send(self, message: AgentMessage) -> None:
        """Send a message — stores in history and target queue."""
        self._sent.append(message)
        if message.recipient:
            queue = self._queues.setdefault(message.recipient, asyncio.Queue())
            await queue.put(message)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        """Receive next message for agent_id, or None on timeout."""
        queue = self._queues.setdefault(agent_id, asyncio.Queue())
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def shutdown(self) -> None:
        """Clear all queues and history."""
        self._sent.clear()
        self._queues.clear()

    # ── Query helpers ─────────────────────────────────────────────

    def messages_to(self, recipient: str) -> list[AgentMessage]:
        """All messages sent to a specific recipient."""
        return [m for m in self._sent if m.recipient == recipient]

    def messages_from(self, sender: str) -> list[AgentMessage]:
        """All messages sent by a specific sender."""
        return [m for m in self._sent if m.sender == sender]

    def messages_of_kind(self, kind: MessageKind) -> list[AgentMessage]:
        """All messages of a specific kind."""
        return [m for m in self._sent if m.kind == kind]

    def messages_with_correlation(self, correlation_id: str) -> list[AgentMessage]:
        """All messages matching a correlation_id."""
        return [m for m in self._sent if m.correlation_id == correlation_id]

    def count(self) -> int:
        """Total number of sent messages."""
        return len(self._sent)

    def clear(self) -> None:
        """Clear sent history (but keep queues alive)."""
        self._sent.clear()


__all__ = ["InMemoryBus", "MockBus"]
