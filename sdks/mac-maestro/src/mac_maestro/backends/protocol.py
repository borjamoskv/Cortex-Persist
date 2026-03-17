from __future__ import annotations

from typing import Protocol

from ..models import AXNodeSnapshot, ElementMatch, PressAction, TypeAction


class BackendProtocol(Protocol):
    def snapshot(self, bundle_id: str) -> AXNodeSnapshot:
        ...

    def click(self, match: ElementMatch) -> None:
        ...

    def type_text(self, action: TypeAction, match: ElementMatch | None) -> None:
        ...

    def press(self, action: PressAction) -> None:
        ...
