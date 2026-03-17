"""CORTEX v6.0 — Human Escalation Protocol.

Provides the escalation mechanism when an agent enters
an unrecoverable state or requires human intervention
(e.g., repeating the same error, missing API key).
"""

<<<<<<< HEAD
from typing import Any
=======
from typing import Any, Optional
>>>>>>> origin/main


class HumanEscalationPulse(Exception):
    """Exception raised to halt an agent and escalate to a human."""

<<<<<<< HEAD
    def __init__(self, agent_id: str, reason: str, context: dict[str, Any] | None = None):
=======
    def __init__(self, agent_id: str, reason: str, context: Optional[dict[str, Any]] = None):
>>>>>>> origin/main
        super().__init__(f"Agent {agent_id} halted: {reason}")
        self.agent_id = agent_id
        self.reason = reason
        self.context = context or {}


<<<<<<< HEAD
async def emit_swarm_signal(bus, agent_id: str, event_type: str, payload: dict | None = None):
=======
async def emit_swarm_signal(bus, agent_id: str, event_type: str, payload: Optional[dict] = None):
>>>>>>> origin/main
    """Helper to emit swarm signals asynchronously."""
    if bus is None:
        return
    await bus.emit(event_type=event_type, payload=payload or {}, source=agent_id, project="cortex")


<<<<<<< HEAD
def emit_swarm_signal_sync(bus, agent_id: str, event_type: str, payload: dict | None = None):
=======
def emit_swarm_signal_sync(bus, agent_id: str, event_type: str, payload: Optional[dict] = None):
>>>>>>> origin/main
    """Helper to emit swarm signals synchronously."""
    if bus is None:
        return
    bus.emit(event_type=event_type, payload=payload or {}, source=agent_id, project="cortex")
