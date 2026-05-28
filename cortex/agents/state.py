"""CORTEX Agent Runtime — State & Working Memory.

AgentStatus tracks lifecycle phase.
AgentState holds runtime metadata.
WorkingMemory provides isolated per-agent scratch space.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Lifecycle status of an agent."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass()
class AgentState:
    """Mutable runtime state for an agent instance."""

    status: AgentStatus = AgentStatus.IDLE
    current_goal: str | None = None
    memory_ref: str | None = None
    last_heartbeat_ts: float | None = None
    error_count: int = 0
    consecutive_errors: int = 0
    total_messages_processed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_error(self, error: str) -> None:
        """Record an error occurrence."""
        self.error_count += 1
        self.consecutive_errors += 1
        self.metadata["last_error"] = error

    def record_success(self) -> None:
        """Reset consecutive error counter on successful processing."""
        self.consecutive_errors = 0

    def record_message_processed(self) -> None:
        """Increment message counter."""
        self.total_messages_processed += 1


@dataclass()
class WorkingMemory:
    """Isolated per-agent working memory.

    This is ephemeral scratch space — NOT persistent CORTEX facts.
    Agents must propose facts through guards to persist knowledge.
    """

    active_tasks: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    scratchpad: dict[str, Any] = field(default_factory=dict)

    def clear(self) -> None:
        """Reset working memory."""
        self.active_tasks.clear()
        self.hypotheses.clear()
        self.scratchpad.clear()
