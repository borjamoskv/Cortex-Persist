"""Mac-Maestro-Ω — CGEvent mouse control (Vector D)."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("mac_maestro.cgevents")

try:
    from Quartz import (
        CGEventCreate,
        CGEventCreateMouseEvent,
        CGEventPost,
        CGPointMake,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseDragged,
        kCGEventLeftMouseUp,
        kCGEventMouseMoved,
        kCGHIDEventTap,
        kCGMouseButtonLeft,
    )
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False

from .models import ActionFailed


def click_at(x: float, y: float) -> None:
    """Click at absolute screen coordinates (x, y)."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for CGEvent.")

    point = CGPointMake(x, y)
    down = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft,
    )
    up = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, up)


def drag_to(
    x1: float, y1: float, x2: float, y2: float,
    steps: int = 20,
) -> None:
    """Drag from (x1,y1) to (x2,y2)."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for CGEvent.")

    start = CGPointMake(x1, y1)
    down = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseDown, start, kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)

    for i in range(1, steps + 1):
        frac = i / steps
        cx = x1 + (x2 - x1) * frac
        cy = y1 + (y2 - y1) * frac
        pt = CGPointMake(cx, cy)
        move = CGEventCreateMouseEvent(
            None, kCGEventLeftMouseDragged, pt, kCGMouseButtonLeft,
        )
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.01)

    end = CGPointMake(x2, y2)
    up = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseUp, end, kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, up)
