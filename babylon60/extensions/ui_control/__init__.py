# [C5-REAL] Exergy-Maximized
"""
cortex.ui_control - macOS sovereign desktop control.

Engines:
    - MaestroUI: Unified orchestrator (recommended entry point)
    - AccessibilityEngine: Direct bridge to macOS Accessibility APIs
    - KeyboardEngine: Keystroke injection via AppleScript System Events
    - MouseEngine: Mouse control via CoreGraphics (Quartz)
    - WindowEngine: Window management via AppleScript System Events

Functions:
    - run_applescript: Asynchronous AppleScript execution with timeout
    - capture_screen: Screen capture via CoreGraphics
"""

from babylon60.extensions.ui_control.accessibility import AccessibilityEngine
from babylon60.extensions.ui_control.applescript import (
    get_clipboard,
    get_frontmost_app,
    is_app_running,
    run_applescript,
    set_clipboard,
)
from babylon60.extensions.ui_control.bootstrapper import PermsBootstrapper
from babylon60.extensions.ui_control.feedback_loop import UIFeedbackLoop
from babylon60.extensions.ui_control.keyboard import KeyboardEngine
from babylon60.extensions.ui_control.maestro import MaestroUI
from babylon60.extensions.ui_control.models import (
    AppTarget,
    AXElement,
    InteractionResult,
    KeyCombo,
    Point,
    UITimeoutError,
    WindowInfo,
)
from babylon60.extensions.ui_control.mouse import MouseEngine
from babylon60.extensions.ui_control.vision import VisionEngine
from babylon60.extensions.ui_control.window import WindowEngine

__all__ = [
    "AXElement",
    "AccessibilityEngine",
    "AppTarget",
    "InteractionResult",
    "KeyCombo",
    "KeyboardEngine",
    "MaestroUI",
    "MouseEngine",
    "Point",
    "UITimeoutError",
    "VisionEngine",
    "WindowEngine",
    "WindowInfo",
    "UIFeedbackLoop",
    "PermsBootstrapper",
    "get_clipboard",
    "get_frontmost_app",
    "is_app_running",
    "run_applescript",
    "set_clipboard",
]
