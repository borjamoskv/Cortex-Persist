from __future__ import annotations

from .errors import SafetyViolationError
from .models import ClickAction, PressAction, TypeAction, UIAction

DANGEROUS_TITLES = {
    "delete",
    "erase",
    "remove",
    "trash",
    "empty trash",
    "factory reset",
    "sign out",
    "log out",
    "shutdown",
    "restart",
    "quit without saving",
}


class SafetyPolicy:
    def __init__(self, allow_destructive: bool = False) -> None:
        self.allow_destructive = allow_destructive

    def validate(self, action: UIAction) -> None:
        match action:
            case ClickAction():
                self._validate_click(action)
            case TypeAction():
                self._validate_type(action)
            case PressAction():
                self._validate_press(action)
            case _:
                raise SafetyViolationError(f"Unknown action type: {type(action)!r}")

    def _validate_click(self, action: ClickAction) -> None:
        title = (action.title or action.contains_text or "").strip().casefold()
        if not self.allow_destructive and title in DANGEROUS_TITLES:
            raise SafetyViolationError(f"Blocked destructive click target: {title}")

    def _validate_type(self, action: TypeAction) -> None:
        if len(action.text) > 10000:
            raise SafetyViolationError("Refusing to type absurd payload >10k chars.")

    def _validate_press(self, action: PressAction) -> None:
        if (
            not self.allow_destructive and action.key_code == 53
        ):  # Escape usually safe, just example
            return
