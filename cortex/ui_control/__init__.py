"""
cortex.ui_control — Control soberano de escritorio macOS.

Motores:
    - MaestroUI: Orquestador unificado (punto de entrada recomendado)
    - AccessibilityEngine: Puente directo a macOS Accessibility APIs
    - KeyboardEngine: Inyección de teclas vía AppleScript System Events
    - MouseEngine: Control de mouse vía CoreGraphics (Quartz)
    - WindowEngine: Gestión de ventanas vía AppleScript System Events

Funciones:
    - run_applescript: Ejecución asíncrona de AppleScript con timeout
    - capture_screen: Captura de pantalla vía CoreGraphics
"""

from cortex.ui_control.accessibility import AccessibilityEngine
from cortex.ui_control.applescript import (
    get_clipboard,
    get_frontmost_app,
    is_app_running,
    run_applescript,
    set_clipboard,
)
from cortex.ui_control.keyboard import KeyboardEngine
from cortex.ui_control.maestro import MaestroUI
from cortex.ui_control.models import (
    AXElement,
    AppTarget,
    InteractionResult,
    KeyCombo,
    Point,
    UITimeoutError,
    WindowInfo,
)
from cortex.ui_control.mouse import MouseEngine
from cortex.ui_control.vision import VisionEngine
from cortex.ui_control.window import WindowEngine

__all__ = [
    "AccessibilityEngine",
    "AXElement",
    "AppTarget",
    "InteractionResult",
    "KeyboardEngine",
    "KeyCombo",
    "MaestroUI",
    "MouseEngine",
    "Point",
    "UITimeoutError",
    "VisionEngine",
    "WindowEngine",
    "WindowInfo",
    "get_clipboard",
    "get_frontmost_app",
    "is_app_running",
    "run_applescript",
    "set_clipboard",
]
