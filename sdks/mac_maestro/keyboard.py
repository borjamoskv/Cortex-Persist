"""Mac-Maestro-Ω — Keyboard input (Vector C)."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("mac_maestro.keyboard")

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,  # noqa: F401
        kCGEventKeyDown,  # noqa: F401
        kCGEventKeyUp,  # noqa: F401
        kCGHIDEventTap,
    )

    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False

from .models import ActionFailed


def type_text(text: str, method: str = "cgevent") -> None:
    """Type text using CGEvent keyboard events."""
    if method == "cgevent":
        if not QUARTZ_AVAILABLE:
            raise ActionFailed("Quartz framework not available for keyboard input.")
        for char in text:
            _press_char_cgevent(char)
            time.sleep(0.02)
    else:
        raise ActionFailed(f"Unknown typing method: {method}")


def press_key(keycode: int) -> None:
    """Press and release a key by keycode."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for keyboard input.")

    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def _press_char_cgevent(char: str) -> None:
    """Press a single character via CGEvent."""
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available.")

    # Use keycode 0 as placeholder — real impl would map chars to keycodes
    down = CGEventCreateKeyboardEvent(None, 0, True)
    up = CGEventCreateKeyboardEvent(None, 0, False)

    from Quartz import CGEventKeyboardSetUnicodeString

    CGEventKeyboardSetUnicodeString(down, len(char), char)
    CGEventKeyboardSetUnicodeString(up, len(char), char)

    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)
