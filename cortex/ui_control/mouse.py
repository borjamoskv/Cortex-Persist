import logging
import time
from typing import TYPE_CHECKING, Optional

try:
    import Quartz.CoreGraphics as CG  # type: ignore[reportMissingImports]
except ImportError:
    CG = None

from cortex.ui_control.models import InteractionResult, Point

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.ui_control.mouse")

# ─── Constantes ──────────────────────────────────────────────────
HUMAN_CLICK_DELAY = 0.1  # Segundos entre down/up


# pyright: reportAttributeAccessIssue=false
class MouseEngine:
    """
    Control de mouse de bajo nivel usando macOS CoreGraphics (Quartz).
    Simula interacciones físicas: click, doble click, drag, scroll.
    """

    def __init__(self, engine: Optional["CortexEngine"] = None) -> None:
        self.engine = engine

    def _post_event(self, event_type: int, point: Point, button: int = 0) -> None:
        """Publica un evento de mouse al sistema operativo."""
        if not CG:
            return
        event = CG.CGEventCreateMouseEvent(None, event_type, (point.x, point.y), button)
        CG.CGEventPost(CG.kCGHIDEventTap, event)

    def click(self, x: int, y: int, button: str = "left") -> InteractionResult:
        """Click simple (down + up) en coordenadas específicas."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics no disponible")

        p = Point(x, y)
        btn = CG.kCGMouseButtonLeft if button == "left" else CG.kCGMouseButtonRight
        down = CG.kCGEventLeftMouseDown if button == "left" else CG.kCGEventRightMouseDown
        up = CG.kCGEventLeftMouseUp if button == "left" else CG.kCGEventRightMouseUp

        self._post_event(down, p, btn)
        time.sleep(HUMAN_CLICK_DELAY)
        self._post_event(up, p, btn)

        return InteractionResult(success=True)

    def double_click(self, x: int, y: int) -> InteractionResult:
        """Doble click con clickCount=2 nativo (más fiable que dos clicks)."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics no disponible")

        p = Point(x, y)
        btn = CG.kCGMouseButtonLeft

        # Primer click
        down1 = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseDown, (p.x, p.y), btn)
        CG.CGEventSetIntegerValueField(down1, CG.kCGMouseEventClickState, 1)
        CG.CGEventPost(CG.kCGHIDEventTap, down1)

        up1 = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseUp, (p.x, p.y), btn)
        CG.CGEventSetIntegerValueField(up1, CG.kCGMouseEventClickState, 1)
        CG.CGEventPost(CG.kCGHIDEventTap, up1)

        time.sleep(0.05)

        # Segundo click con clickCount=2
        down2 = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseDown, (p.x, p.y), btn)
        CG.CGEventSetIntegerValueField(down2, CG.kCGMouseEventClickState, 2)
        CG.CGEventPost(CG.kCGHIDEventTap, down2)

        up2 = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseUp, (p.x, p.y), btn)
        CG.CGEventSetIntegerValueField(up2, CG.kCGMouseEventClickState, 2)
        CG.CGEventPost(CG.kCGHIDEventTap, up2)

        return InteractionResult(success=True)

    def right_click(self, x: int, y: int) -> InteractionResult:
        """Click derecho (menú contextual) en coordenadas específicas."""
        return self.click(x, y, button="right")

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
        steps: int = 20,
    ) -> InteractionResult:
        """
        Drag-and-drop con movimiento interpolado.
        Simula un arrastre humano con pasos intermedios.
        """
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics no disponible")

        btn = CG.kCGMouseButtonLeft
        step_delay = duration / steps

        # Mouse down en origen
        down = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseDown, (from_x, from_y), btn)
        CG.CGEventPost(CG.kCGHIDEventTap, down)
        time.sleep(0.05)

        # Movimiento interpolado
        for i in range(1, steps + 1):
            t = i / steps
            cx = from_x + int((to_x - from_x) * t)
            cy = from_y + int((to_y - from_y) * t)
            drag_ev = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseDragged, (cx, cy), btn)
            CG.CGEventPost(CG.kCGHIDEventTap, drag_ev)
            time.sleep(step_delay)

        # Mouse up en destino
        up = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseUp, (to_x, to_y), btn)
        CG.CGEventPost(CG.kCGHIDEventTap, up)

        return InteractionResult(success=True)

    def move(self, x: int, y: int) -> InteractionResult:
        """Mueve el cursor a coordenadas específicas."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics no disponible")

        self._post_event(CG.kCGEventMouseMoved, Point(x, y))
        return InteractionResult(success=True)

    def scroll(self, clicks: int) -> InteractionResult:
        """Simula scroll de rueda. Positivo=arriba, negativo=abajo."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics no disponible")

        event = CG.CGEventCreateScrollWheelEvent(None, CG.kCGScrollEventUnitLine, 1, clicks)
        CG.CGEventPost(CG.kCGHIDEventTap, event)
        return InteractionResult(success=True)
