from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KeyModifier(str, Enum):
    COMMAND = "command"
    SHIFT = "shift"
    OPTION = "option"
    CONTROL = "control"


class AXNodeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    role: str
    subrole: str | None = None
    title: str | None = None
    description: str | None = None
    value: str | None = None
    enabled: bool = True
    visible: bool = True
    focused: bool = False
    children: list[AXNodeSnapshot] = Field(default_factory=list)


class ElementSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    subrole: str | None = None
    title: str | None = None
    description: str | None = None
    value: str | None = None
    contains_text: str | None = None
    enabled: bool | None = True
    visible: bool | None = True


class ElementMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    node: AXNodeSnapshot


class ClickAction(ElementSelector):
    kind: Literal["click"] = "click"


class TypeAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["type"] = "type"
    text: str
    clear_first: bool = False
    target: ElementSelector | None = None


class PressAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["press"] = "press"
    key_code: int
    modifiers: list[KeyModifier] = Field(default_factory=list)


UIAction = ClickAction | TypeAction | PressAction


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal[
        "snapshot",
        "match",
        "safety",
        "execute",
        "result",
        "error",
    ]
    action_index: int
    action_kind: str
    message: str
    payload: dict = Field(default_factory=dict)


class RunTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    events: list[TraceEvent] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


def walk_nodes(root: AXNodeSnapshot) -> Sequence[AXNodeSnapshot]:
    result: list[AXNodeSnapshot] = []

    def _walk(node: AXNodeSnapshot) -> None:
        result.append(node)
        for child in node.children:
            _walk(child)

    _walk(root)
    return result


AXNodeSnapshot.model_rebuild()
