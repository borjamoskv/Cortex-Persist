import logging
import time
from typing import TYPE_CHECKING, Optional

try:
    import Quartz.CoreGraphics as CG
except ImportError:
    CG = None

from cortex.ui_control.models import InteractionResult, Point

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.ui_control.mouse")

# ─── Constants ──────────────────────────────────────────────────
HUMAN_CLICK_DELAY = 0.1  # Seconds


class MouseEngine:
    """
    Low-level mouse control using macOS CoreGraphics (Quartz).
    Enables physical interaction simulation.
    """

    def __init__(self, engine: Optional["CortexEngine"] = None) -> None:
        self.engine = engine

    def _post_event(
        self, event_type: int, point: Point, button: int = 0
    ) -> None:
        """Helper to post a mouse event to the OS."""
        if not CG:
            return

        # Default to Left Mouse Button if button is 0 and not specified
        # CG.kCGMouseButtonLeft is 0

        event = CG.CGEventCreateMouseEvent(
            None, event_type, (point.x, point.y), button
        )
        CG.CGEventPost(CG.kCGHIDEventTap, event)

    def click(self, x: int, y: int, button: str = "left") -> InteractionResult:
        """Simulates a full click (down + up) at specific coordinates."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics not available")

        p = Point(x, y)
        btn = CG.kCGMouseButtonLeft if button == "left" else CG.kCGMouseButtonRight

        down = CG.kCGEventLeftMouseDown if button == "left" else CG.kCGEventRightMouseDown
        up = CG.kCGEventLeftMouseUp if button == "left" else CG.kCGEventRightMouseUp

        self._post_event(down, p, btn)
        time.sleep(HUMAN_CLICK_DELAY)  # Brief delay to simulate human timing
        self._post_event(up, p, btn)

        return InteractionResult(success=True)

    def move(self, x: int, y: int) -> InteractionResult:
        """Moves the cursor to coordinates."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics not available")

        self._post_event(CG.kCGEventMouseMoved, Point(x, y))
        return InteractionResult(success=True)

    def scroll(self, clicks: int) -> InteractionResult:
        """Simulates mouse wheel scroll."""
        if not CG:
            return InteractionResult(success=False, error="CoreGraphics not available")

        event = CG.CGEventCreateScrollWheelEvent(None, CG.kCGScrollEventUnitLine, 1, clicks)
        CG.CGEventPost(CG.kCGHIDEventTap, event)
        return InteractionResult(success=True)
