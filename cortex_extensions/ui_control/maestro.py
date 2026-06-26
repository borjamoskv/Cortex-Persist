# [C5-REAL] Exergy-Maximized
"""
MaestroUI - Orquestador soberano de control de escritorio macOS.

Integra todos los motores (Accessibility, Keyboard, Mouse, Window, Vision)
en una interfaz unificada con lógica de reintento.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from cortex_extensions.ui_control.accessibility import AccessibilityEngine
from cortex_extensions.ui_control.applescript import (
    is_app_running,
    run_applescript,
)
from cortex_extensions.ui_control.keyboard import KeyboardEngine
from cortex_extensions.ui_control.models import (
    AppTarget,
    InteractionResult,
)
from cortex_extensions.ui_control.mouse import MouseEngine
from cortex_extensions.ui_control.vision import VisionEngine
from cortex_extensions.ui_control.window import WindowEngine

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex_extensions.ui_control.maestro")

# Constantes de reintentos
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # segundos


class MaestroUI:
    """
    Orquestador de automatización de escritorio macOS.

    Combina todos los sub-motores (accessibility, keyboard, mouse, window, vision)
    bajo una API unificada con reintentos automáticos.
    """

    def __init__(self, engine: CortexEngine | None = None) -> None:
        self.engine = engine
        self.accessibility = AccessibilityEngine(engine)
        self.keyboard = KeyboardEngine(engine)
        self.mouse = MouseEngine(engine)
        self.window = WindowEngine(engine)
        self.vision = VisionEngine(engine)

    # ─── Utilidades ─────────────────────────────────────────────

    async def _retry(
        self,
        coro_fn,
        *args,
        retries: int = MAX_RETRIES,
        **kwargs,
    ) -> InteractionResult:
        """Ejecuta una coroutine con reintentos automáticos."""
        last_error = ""
        for attempt in range(retries):
            result = await coro_fn(*args, **kwargs)
            if result.success:
                return result
            last_error = result.error or ""
            logger.warning("Intento %d/%d falló: %s", attempt + 1, retries, last_error)
            if attempt < retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        return InteractionResult(
            success=False,
            error=f"Fallido tras {retries} intentos: {last_error}",
        )

    def __getattr__(self, name: str) -> Any:
        # Mapping for renamed methods in legacy facade
        aliases = {
            "move_window": (self.window, "move"),
            "resize_window": (self.window, "resize"),
            "minimize_window": (self.window, "minimize"),
            "restore_window": (self.window, "restore"),
            "fullscreen_window": (self.window, "fullscreen"),
            "close_window": (self.window, "close_window"),
            "get_frontmost_window": (self.window, "get_frontmost"),
            "move_cursor": (self.mouse, "move"),
            "screenshot": (self.vision, "capture_screen"),
            "click_element": (self.accessibility, "perform_click"),
        }

        if name in aliases:
            engine, real_name = aliases[name]
            method = getattr(engine, real_name)
            if name in ("click_element",):
                return lambda *a, **kw: self._retry(method, *a, **kw)
            return method

        # Auto-introspect sub-engines
        for engine in (self.accessibility, self.keyboard, self.mouse, self.window, self.vision):
            if hasattr(engine, name):
                method = getattr(engine, name)
                # Apply retry for keyboard methods automatically if async
                if engine is self.keyboard and asyncio.iscoroutinefunction(method):
                    return lambda *a, **kw: self._retry(method, *a, **kw)
                return method

        # Applescript fallbacks
        import cortex_extensions.ui_control.applescript as applescript

        if hasattr(applescript, name):
            return getattr(applescript, name)

        if name == "clipboard_set":
            return applescript.set_clipboard
        if name == "clipboard_get":
            return applescript.get_clipboard
        if name == "run_script":
            return lambda script: applescript.run_applescript(script, require_success=False)

        raise AttributeError(f"'MaestroUI' object has no attribute '{name}'")

    async def activate_app(self, target: AppTarget) -> InteractionResult:
        """Activa una aplicación en primer plano."""
        script = f'tell application "{target.name}" to activate'
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def inject_keystroke(
        self,
        target: AppTarget,
        key: str,
        modifiers: list[str] | None = None,
    ) -> InteractionResult:
        """Activa la app y envía un keystroke de AppleScript."""
        modifiers = modifiers or []
        if not await is_app_running(target.name):
            return InteractionResult(success=False, error=f"{target.name} is not running")

        modifier_clause = ""
        if modifiers:
            modifier_clause = f" using {{{', '.join(modifiers)}}}"

        script = f"""
        tell application "{target.name}" to activate
        delay 0.3
        tell application "System Events"
            keystroke "{key}"{modifier_clause}
        end tell
        """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def click_menu_item(
        self,
        target: AppTarget,
        menu_path: list[str],
    ) -> InteractionResult:
        """Activa la app y pulsa un ítem de menú anidado."""
        if len(menu_path) < 2:
            return InteractionResult(
                success=False,
                error="Menu path must have at least 2 items: menu and item",
            )

        menu_name = menu_path[0]
        item_name = menu_path[-1]

        script = f"""
        tell application "{target.name}" to activate
        delay 0.3
        tell application "System Events"
            tell process "{target.name}"
                click menu item "{item_name}" of menu "{menu_name}" of menu bar 1
            end tell
        end tell
        """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))
