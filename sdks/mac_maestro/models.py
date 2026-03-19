"""Mac-Maestro-Ω — Core data models for sovereign macOS automation."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any


@dataclasses.dataclass
class ElementMatch:
    """Result of a semantic element search over an AX tree."""

    ref: Any
    role: str | None
    subrole: str | None
    title: str | None
    value: str | None
    identifier: str | None
    description: str | None
    position: tuple[float, float] | None
    size: tuple[float, float] | None
    score: float
    reasons: list[str]

    @property
    def center(self) -> tuple[float, float] | None:
        """Calculate click-center from position + size."""
        if self.position is not None and self.size is not None:
            return (
                self.position[0] + self.size[0] / 2,
                self.position[1] + self.size[1] / 2,
            )
        return None


@dataclasses.dataclass
class AXNodeSnapshot:
    role: str | None
    subrole: str | None
    title: str | None
    value: str | None
    identifier: str | None
    description: str | None
    enabled: bool | None
    focused: bool | None
    position: tuple[float, float] | None
    size: tuple[float, float] | None
    path: tuple[int, ...]
    children: list[AXNodeSnapshot]
    _ref: Any = None


@dataclasses.dataclass
class ResolvedTarget:
    """Normalized output of the Element Resolution Pipeline."""

    pid: int
    app_name: str
    bundle_id: str
    window_title: str | None
    element: ElementMatch | None
    position: tuple[float, float] | None
    resolution_method: str
    degraded: bool
    candidates_count: int = 0
    confidence: float = 0.0


@dataclasses.dataclass
class UIAction:
    name: str
    vector: str
    target_query: dict[str, Any] = dataclasses.field(default_factory=dict)
    preconditions: list[Callable[[], bool]] = dataclasses.field(
        default_factory=list,
    )
    executor: Callable[[], Any] | None = None
    postconditions: list[Callable[[], bool]] = dataclasses.field(
        default_factory=list,
    )
    fallbacks: list[UIAction] = dataclasses.field(default_factory=list)
    idempotent: bool = False
    retry_limit: int = 1
    unsafe: bool = False


class ActionFailed(Exception):
    """Raised when an action fails."""
