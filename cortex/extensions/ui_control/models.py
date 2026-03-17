import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.extensions.ui_control")


# ─── Exceptions ──────────────────────────────────────────────────


class UIControlError(Exception):
    """Base exception for all UI control errors."""

    pass


class AppNotRunningError(UIControlError):
    """When the target application is not currently active."""

    pass


class UIElementNotFoundError(UIControlError):
    """When an AppleScript cannot find the requested window, button, or element."""

    pass


class AppleScriptExecutionError(UIControlError):
    """When osascript returns a non-zero exit code due to syntax or runtime errors."""

    def __init__(self, message: str, returncode: int, stderr: str):
        super().__init__(f"{message} (Exit Code: {returncode}): {stderr}")
        self.returncode = returncode
        self.stderr = stderr


class UITimeoutError(UIControlError):
    """When an element or condition is not met within the allotted time."""

    pass


# ─── Data Models ─────────────────────────────────────────────────


@dataclass
class Point:
    """Represents a coordinate on the screen."""

    x: int
    y: int


@dataclass
class AXElement:
    """Represents a macOS UI element from the Accessibility tree."""

    role: str
    subrole: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    identifier: Optional[str] = None
    value: Optional[str] = None
    native_ref: object = None
    depth: int = 0
    children: list["AXElement"] = field(default_factory=list)


@dataclass
class AppTarget:
    """Represents an application to target."""

    name: str
    bundle_id: Optional[str] = None


@dataclass
class InteractionResult:
    """Result of a UI interaction."""

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class KeyCombo:
    """Type-safe keystroke specification."""

    key: str
    modifiers: list[str] = field(default_factory=list)

    def to_applescript(self) -> str:
        """Converts to AppleScript keystroke fragment."""
        # Special keys use 'key code' instead of 'keystroke'
        special = SPECIAL_KEY_MAP.get(self.key)
        if special is not None:
            action = f"key code {special}"
        else:
            action = f'keystroke "{self.key}"'

        if self.modifiers:
            mods = ", ".join(f"{m} down" if "down" not in m else m for m in self.modifiers)
            action += f" using {{{mods}}}"
        return action


@dataclass
class WindowInfo:
    """Represents a macOS application window."""

    title: str
    app_name: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    minimized: bool = False
    fullscreen: bool = False
    index: int = 1


# ─── Key Maps ────────────────────────────────────────────────────

SPECIAL_KEY_MAP: dict[str, int] = {
    "return": 36,
    "enter": 76,
    "tab": 48,
    "space": 49,
    "delete": 51,
    "escape": 53,
    "esc": 53,
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
    "home": 115,
    "end": 119,
    "pageup": 116,
    "pagedown": 121,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}
