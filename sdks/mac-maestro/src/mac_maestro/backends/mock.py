from __future__ import annotations

from ..errors import ActionExecutionError
from ..models import AXNodeSnapshot, ElementMatch, PressAction, TypeAction


class MockBackend:
    def __init__(self, root: AXNodeSnapshot) -> None:
        self.root = root
        self.executed: list[dict] = []

    def snapshot(self, bundle_id: str) -> AXNodeSnapshot:
        return self.root

    def click(self, match: ElementMatch) -> None:
        self.executed.append({"kind": "click", "element_id": match.element_id})

    def type_text(self, action: TypeAction, match: ElementMatch | None) -> None:
        if match is None and action.target is not None:
            raise ActionExecutionError("Type action expected a resolved target.")
        self.executed.append(
            {
                "kind": "type",
                "text": action.text,
                "element_id": None if match is None else match.element_id,
            }
        )

    def press(self, action: PressAction) -> None:
        self.executed.append(
            {
                "kind": "press",
                "key_code": action.key_code,
                "modifiers": [m.value for m in action.modifiers],
            }
        )
