from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MacAction:
    action: str  # click, type, select, inspect, hotkey
    app: str
    role: str | None = None
    title: str | None = None
    identifier: str | None = None
    payload: Any | None = None
    unsafe_override: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MacIntent:
    goal: str
    actions: list[MacAction]
    correlation_id: str | None = None
    trace_id: str | None = None
