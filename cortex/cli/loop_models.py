
"""loop_models — Data models for the CORTEX Execution Loop.

Extracted from loop_cmds.py to satisfy the Landauer LOC barrier.
Pure dataclasses — no I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.utils.time import utc_now

__all__ = ["TaskStatus", "PersistenceType", "TaskResult", "LoopSession"]


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PersistenceType(Enum):
    DECISION = "decision"
    ERROR = "error"
    GHOST = "ghost"
    BRIDGE = "bridge"
    KNOWLEDGE = "knowledge"


@dataclass
class TaskResult:
    """Result of a single task execution."""

    task: str
    status: TaskStatus
    output: str
    duration_ms: float
    persisted_ids: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class LoopSession:
    """Tracks the full execution loop session."""

    project: str
    source: str
    started_at: str = field(default_factory=lambda: utc_now().isoformat())
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_persisted: int = 0
    results: list[TaskResult] = field(default_factory=list)
    active: bool = True
