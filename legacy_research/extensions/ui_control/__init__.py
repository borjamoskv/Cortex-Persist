# [C5-REAL] Exergy-Maximized
"""
cortex.ui_control - Control soberano de escritorio macOS.

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

from legacy_research.extensions.ui_control.accessibility import AccessibilityEngine
from legacy_research.extensions.ui_control.applescript import (
    get_clipboard,
    get_frontmost_app,
    is_app_running,
    run_applescript,
    set_clipboard,
)
from legacy_research.extensions.ui_control.bootstrapper import PermsBootstrapper
from legacy_research.extensions.ui_control.feedback_loop import UIFeedbackLoop
from legacy_research.extensions.ui_control.keyboard import KeyboardEngine
from legacy_research.extensions.ui_control.maestro import MaestroUI
from legacy_research.extensions.ui_control.models import (
    AppTarget,
    AXElement,
    InteractionResult,
    KeyCombo,
    Point,
    UITimeoutError,
    WindowInfo,
)
from legacy_research.extensions.ui_control.mouse import MouseEngine
from legacy_research.extensions.ui_control.vision import VisionEngine
from legacy_research.extensions.ui_control.window import WindowEngine

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
