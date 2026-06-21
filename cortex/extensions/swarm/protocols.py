# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.swarm.protocols")


class SwarmIntent(str, Enum):
    DISCOVERY = "discovery"
    ROADBLOCK = "roadblock"
    VERIFICATION = "verification"
    COMPLETION = "completion"
    HEALING = "healing"


class AgentRole(str, Enum):
    CAPATAZ = "capataz"
    WORKER = "worker"
    ELDER = "elder"


@dataclass
class SwarmSignalSchema:
    mission_id: str
    agent_id: str
    intent: SwarmIntent
    payload: dict[str, Any]
    role: AgentRole = AgentRole.WORKER
    confidence: float = 1.0
    exergy_spent: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.fromtimestamp(
            time.monotonic(), tz=timezone.utc
        ).isoformat()
    )

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SwarmSignalSchema:
        if "intent" in data:
            data["intent"] = SwarmIntent(data["intent"])
        if "role" in data:
            data["role"] = AgentRole(data["role"])
        return cls(**data)


def validate_swarm_signal(data: dict[str, Any]) -> bool:
    """Validate that a signal matches the Ω₁₄ schema."""
    try:
        SwarmSignalSchema.from_dict(data)
        return True
    except (ValueError, KeyError, TypeError) as e:
        logger.error("Invalid swarm signal schema: %s", e)
        return False
