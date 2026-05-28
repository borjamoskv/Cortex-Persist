"""
CORTEX v5.1 — SovereignGate Models.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .enums import ActionLevel, ActionStatus, GatePolicy

__all__ = ["PendingAction", "GatePolicy"]


@dataclass
class PendingAction:
    """An L3 action awaiting operator approval."""

    action_id: str
    level: ActionLevel
    description: str
    command: Optional[list[str]] = None
    project: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    executed_at: Optional[float] = None
    hmac_challenge: str = ""
    operator_id: Optional[str] = None
    result: Optional[dict[str, Any]] = None

    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if the action has exceeded its timeout."""
        return time.time() - self.created_at > timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses and audit log."""
        return {
            "action_id": self.action_id,
            "level": self.level.value,
            "description": self.description,
            "command": self.command,
            "project": self.project,
            "status": self.status.value,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "approved_at": (
                datetime.fromtimestamp(self.approved_at, tz=timezone.utc).isoformat()
                if self.approved_at
                else None
            ),
            "operator_id": self.operator_id,
        }
