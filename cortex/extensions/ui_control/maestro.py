"""
MaestroUI — Orquestador soberano de control de escritorio macOS.

Integra todos los motores (Accessibility, Keyboard, Mouse, Window, Vision)
en una interfaz unificada con lógica de reintento.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from cortex.extensions.ui_control.accessibility import AccessibilityEngine
from cortex.extensions.ui_control.applescript import (
    get_clipboard,
    get_frontmost_app,
    is_app_running,
    run_applescript,
    set_clipboard,
)
from cortex.extensions.ui_control.keyboard import KeyboardEngine
from cortex.extensions.ui_control.models import (
    AppTarget,
    AXElement,
    InteractionResult,
    KeyCombo,
    WindowInfo,
)
from cortex.extensions.ui_control.mouse import MouseEngine
from cortex.extensions.ui_control.vision import VisionEngine
from cortex.extensions.ui_control.window import WindowEngine

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.ui_control.maestro")

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
        coro_fn,  # noqa: ANN001
        *args,
        retries: int = MAX_RETRIES,
        **kwargs,  # noqa: ANN003
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

    # ─── Accesibilidad ──────────────────────────────────────────

    def check_permissions(self) -> bool:
        """Verifica permisos de Accesibilidad del sistema."""
        return self.accessibility.check_permissions()

    def find_element(self, app_name: str, identifier: str) -> AXElement | None:
        """Busca un elemento AX por identificador."""
        return self.accessibility.find_element(app_name, identifier)

    def find_element_by_title(
        self, app_name: str, title: str, max_depth: int = 8
    ) -> AXElement | None:
        """Busca un elemento AX por título."""
        return self.accessibility.find_element_by_title(app_name, title, max_depth)

    def find_elements_by_role(
        self, app_name: str, role: str, max_depth: int = 8
    ) -> list[AXElement]:
        """Devuelve todos los elementos que coinciden con un rol AX."""
        return self.accessibility.find_elements_by_role(app_name, role, max_depth)

    def dump_tree(self, app_name: str, max_depth: int = 5) -> list[AXElement]:
        """Vuelca el árbol completo de accesibilidad de una app."""
        return self.accessibility.dump_tree(app_name, max_depth)

    async def wait_for_element(
        self,
        app_name: str,
        identifier: str,
        timeout: float = 5.0,
    ) -> AXElement | None:
        """Espera a que un elemento aparezca (polling)."""
        return await self.accessibility.wait_for_element(app_name, identifier, timeout)

    async def click_element(self, element: AXElement) -> InteractionResult:
        """Click en un elemento AX con reintentos."""
        return await self._retry(self.accessibility.perform_click, element)

    def get_value(self, element: AXElement) -> str | None:
        """Lee el valor AX de un elemento."""
        return self.accessibility.get_value(element)

    def set_value(self, element: AXElement, value: str) -> InteractionResult:
        """Establece el valor AX de un elemento."""
        return self.accessibility.set_value(element, value)

    # ─── Teclado ────────────────────────────────────────────────

    async def hotkey(
        self, key: str, *modifiers: str, target: AppTarget | None = None
    ) -> InteractionResult:
        """Atajo de teclado (ej: hotkey('c', 'command'))."""
        return await self.keyboard.hotkey(key, *modifiers, target=target)

    async def type_text(
        self, text: str, target: AppTarget | None = None, delay: float = 0.05
    ) -> InteractionResult:
        """Escribe texto (clipboard para cadenas largas, keystroke para cortas)."""
        return await self.keyboard.type_text(text, target=target, delay=delay)

    async def press_special(self, key_name: str, target: AppTarget | None = None) -> InteractionResult:
        """Pulsa una tecla especial (return, tab, escape, flechas)."""
        return await self.keyboard.press_special(key_name, target=target)

    async def press(self, combo: KeyCombo, target: AppTarget | None = None) -> InteractionResult:
        """Pulsa una combinación de teclas."""
        return await self.keyboard.press(combo, target=target)

    # ─── Ratón ──────────────────────────────────────────────────

    def click(self, x: int, y: int, button: str = "left") -> InteractionResult:
        """Click simple en coordenadas."""
        return self.mouse.click(x, y, button)

    def double_click(self, x: int, y: int) -> InteractionResult:
        """Doble click nativo."""
        return self.mouse.double_click(x, y)

    def right_click(self, x: int, y: int) -> InteractionResult:
        """Click derecho (menú contextual)."""
        return self.mouse.right_click(x, y)

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
    ) -> InteractionResult:
        """Drag-and-drop interpolado."""
        return self.mouse.drag(from_x, from_y, to_x, to_y, duration=duration)

    def move_cursor(self, x: int, y: int) -> InteractionResult:
        """Mueve el cursor a coordenadas."""
        return self.mouse.move(x, y)

    def scroll(self, clicks: int) -> InteractionResult:
        """Scroll de rueda. Positivo=arriba, negativo=abajo."""
        return self.mouse.scroll(clicks)

    # ─── Ventanas ───────────────────────────────────────────────

    async def list_windows(self, app_name: str) -> list[WindowInfo]:
        """Lista todas las ventanas de una aplicación."""
        return await self.window.list_windows(app_name)

    async def get_frontmost_window(self) -> WindowInfo | None:
        """Devuelve información de la ventana en primer plano."""
        return await self.window.get_frontmost()

    async def move_window(self, target: AppTarget, x: int, y: int) -> InteractionResult:
        """Mueve la ventana principal de una app."""
        return await self.window.move(target, x, y)

    async def resize_window(self, target: AppTarget, width: int, height: int) -> InteractionResult:
        """Redimensiona la ventana principal de una app."""
        return await self.window.resize(target, width, height)

    async def minimize_window(self, target: AppTarget) -> InteractionResult:
        """Minimiza la ventana principal de una app."""
        return await self.window.minimize(target)

    async def restore_window(self, target: AppTarget) -> InteractionResult:
        """Restaura la ventana minimizada de una app."""
        return await self.window.restore(target)

    async def fullscreen_window(self, target: AppTarget) -> InteractionResult:
        """Alterna pantalla completa de una app."""
        return await self.window.fullscreen(target)

    async def close_window(self, target: AppTarget) -> InteractionResult:
        """Cierra la ventana principal de una app (Cmd+W)."""
        return await self.window.close_window(target)

    # ─── AppleScript Directos ───────────────────────────────────

    async def run_script(self, script: str) -> str | None:
        """Ejecuta un AppleScript arbitrario."""
        return await run_applescript(script, require_success=False)

    async def is_app_running(self, app_name: str) -> bool:
        """Verifica si una app está en ejecución."""
        return await is_app_running(app_name)

    async def get_frontmost_app(self) -> str | None:
        """Devuelve el nombre de la app en primer plano."""
        return await get_frontmost_app()

    async def clipboard_set(self, text: str) -> None:
        """Escribe texto al clipboard."""
        await set_clipboard(text)

    async def clipboard_get(self) -> str | None:
        """Lee el clipboard."""
        return await get_clipboard()

    # ─── Visión ─────────────────────────────────────────────────

    async def screenshot(self, output_path: str | None = None) -> str | None:
        """Captura pantalla y devuelve la ruta al archivo."""
        result = self.vision.capture_screen()
        if result.success:
            return result.output
        return None
