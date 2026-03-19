"""Mac-Maestro-Ω — CGEvent mouse control (Vector D)."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("mac_maestro.cgevents")

try:
    from Quartz import (
        CGEventCreate,  # noqa: F401
        CGEventCreateMouseEvent,
        CGEventPost,
        CGEventSetIntegerValueField,
        CGPointMake,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseDragged,
        kCGEventLeftMouseUp,
        kCGEventMouseMoved,  # noqa: F401
        kCGEventRightMouseDown,
        kCGEventRightMouseUp,
        kCGHIDEventTap,
        kCGMouseButtonLeft,
        kCGMouseButtonRight,
        kCGMouseEventClickState,
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
        None,
        kCGEventLeftMouseDown,
        point,
        kCGMouseButtonLeft,
    )
    up = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseUp,
        point,
        kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, up)


def double_click_at(x: float, y: float) -> None:
    """Double-click at absolute screen coordinates (x, y)."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for CGEvent.")

    point = CGPointMake(x, y)

    # First click
    down1 = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseDown,
        point,
        kCGMouseButtonLeft,
    )
    up1 = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseUp,
        point,
        kCGMouseButtonLeft,
    )
    CGEventSetIntegerValueField(down1, kCGMouseEventClickState, 1)
    CGEventSetIntegerValueField(up1, kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, down1)
    CGEventPost(kCGHIDEventTap, up1)

    time.sleep(0.05)

    # Second click (click state = 2 for double-click)
    down2 = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseDown,
        point,
        kCGMouseButtonLeft,
    )
    up2 = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseUp,
        point,
        kCGMouseButtonLeft,
    )
    CGEventSetIntegerValueField(down2, kCGMouseEventClickState, 2)
    CGEventSetIntegerValueField(up2, kCGMouseEventClickState, 2)
    CGEventPost(kCGHIDEventTap, down2)
    CGEventPost(kCGHIDEventTap, up2)


def right_click_at(x: float, y: float) -> None:
    """Right-click at absolute screen coordinates (x, y)."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for CGEvent.")

    point = CGPointMake(x, y)
    down = CGEventCreateMouseEvent(
        None,
        kCGEventRightMouseDown,
        point,
        kCGMouseButtonRight,
    )
    up = CGEventCreateMouseEvent(
        None,
        kCGEventRightMouseUp,
        point,
        kCGMouseButtonRight,
    )
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, up)


def drag_to(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    steps: int = 20,
) -> None:
    """Drag from (x1,y1) to (x2,y2)."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for CGEvent.")

    start = CGPointMake(x1, y1)
    down = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseDown,
        start,
        kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)

    for i in range(1, steps + 1):
        frac = i / steps
        cx = x1 + (x2 - x1) * frac
        cy = y1 + (y2 - y1) * frac
        pt = CGPointMake(cx, cy)
        move = CGEventCreateMouseEvent(
            None,
            kCGEventLeftMouseDragged,
            pt,
            kCGMouseButtonLeft,
        )
        CGEventPost(kCGHIDEventTap, move)
        time.sleep(0.01)

    end = CGPointMake(x2, y2)
    up = CGEventCreateMouseEvent(
        None,
        kCGEventLeftMouseUp,
        end,
        kCGMouseButtonLeft,
    )
    CGEventPost(kCGHIDEventTap, up)
