import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.ui_control")


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


@dataclass
class Point:
    """Represents a coordinate on the screen."""
    x: int
    y: int


@dataclass
class AXElement:
    """Represents a macOS UI element from the Accessibility tree."""
    role: str
    subrole: str | None = None
    title: str | None = None
    description: str | None = None
    identifier: str | None = None  # Key for language-independent control
    native_ref: object | None = None  # Reference to the AXUIElementRef


@dataclass
class AppTarget:
    """Represents an application to target."""
    name: str  # The human readable name, e.g. "Safari"
    bundle_id: str | None = None  # e.g. "com.apple.Safari"


@dataclass
class InteractionResult:
    """Result of a UI interaction."""
    success: bool
    output: str | None = None
    error: str | None = None
