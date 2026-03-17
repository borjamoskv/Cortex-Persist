"""CORTEX v6.0 — Human Escalation Protocol.

Provides the escalation mechanism when an agent enters
an unrecoverable state or requires human intervention
(e.g., repeating the same error, missing API key).
"""

from typing import Any


class HumanEscalationPulse(Exception):
    """Exception raised to halt an agent and escalate to a human."""

    def __init__(self, agent_id: str, reason: str, context: dict[str, Any] | None = None):
        super().__init__(f"Agent {agent_id} halted: {reason}")
        self.agent_id = agent_id
        self.reason = reason
        self.context = context or {}


async def emit_swarm_signal(bus, agent_id: str, event_type: str, payload: dict | None = None):
    """Helper to emit swarm signals asynchronously."""
    if bus is None:
        return
    await bus.emit(event_type=event_type, payload=payload or {}, source=agent_id, project="cortex")


def emit_swarm_signal_sync(bus, agent_id: str, event_type: str, payload: dict | None = None):
    """Helper to emit swarm signals synchronously."""
    if bus is None:
        return
    bus.emit(event_type=event_type, payload=payload or {}, source=agent_id, project="cortex")
