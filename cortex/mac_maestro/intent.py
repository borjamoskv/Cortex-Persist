from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class MacAction:
    action: str  # click, type, select, inspect, hotkey
    app: str
    role: Optional[str] = None
    title: Optional[str] = None
    identifier: Optional[str] = None
    payload: Optional[Any] = None
    unsafe_override: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MacIntent:
    goal: str
    actions: list[MacAction]
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
