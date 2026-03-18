"""Mac-Maestro-Ω — Keyboard input (Vector C)."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("mac_maestro.keyboard")

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGEventFlagMaskAlternate,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskShift,
        kCGHIDEventTap,
    )

    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False
    kCGEventFlagMaskCommand = 0x00100000
    kCGEventFlagMaskShift = 0x00020000
    kCGEventFlagMaskAlternate = 0x00080000
    kCGEventFlagMaskControl = 0x00040000

from .models import ActionFailed

# ─── Modifier Map ──────────────────────────────────────────────────

MODIFIER_MAP: dict[str, int] = {
    "cmd": kCGEventFlagMaskCommand,
    "command": kCGEventFlagMaskCommand,
    "shift": kCGEventFlagMaskShift,
    "alt": kCGEventFlagMaskAlternate,
    "option": kCGEventFlagMaskAlternate,
    "opt": kCGEventFlagMaskAlternate,
    "ctrl": kCGEventFlagMaskControl,
    "control": kCGEventFlagMaskControl,
}

# ─── Keycode Map (US QWERTY) ──────────────────────────────────────

KEYCODE_MAP: dict[str, int] = {
    "a": 0,
    "b": 11,
    "c": 8,
    "d": 2,
    "e": 14,
    "f": 3,
    "g": 5,
    "h": 4,
    "i": 34,
    "j": 38,
    "k": 40,
    "l": 37,
    "m": 46,
    "n": 45,
    "o": 31,
    "p": 35,
    "q": 12,
    "r": 15,
    "s": 1,
    "t": 17,
    "u": 32,
    "v": 9,
    "w": 13,
    "x": 7,
    "y": 16,
    "z": 6,
    "0": 29,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "5": 23,
    "6": 22,
    "7": 26,
    "8": 28,
    "9": 25,
    "return": 36,
    "enter": 76,
    "tab": 48,
    "space": 49,
    "delete": 51,
    "escape": 53,
    "esc": 53,
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
    "home": 115,
    "end": 119,
    "pageup": 116,
    "pagedown": 121,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
    "-": 27,
    "=": 24,
    "[": 33,
    "]": 30,
    "\\": 42,
    ";": 41,
    "'": 39,
    ",": 43,
    ".": 47,
    "/": 44,
    "`": 50,
}


def parse_hotkey(combo_str: str) -> tuple[int, list[str]]:
    """Parse a hotkey string like 'cmd+shift+s' into (keycode, [modifier_names]).

    Returns:
        Tuple of (keycode, list_of_modifier_names).

    Raises:
        ActionFailed: If the combo is empty or the key is unknown.
    """
    if not combo_str or not combo_str.strip():
        raise ActionFailed("Empty hotkey string.")

    parts = [p.strip().lower() for p in combo_str.split("+")]
    modifiers: list[str] = []
    key_name: str | None = None

    for part in parts:
        if part in MODIFIER_MAP:
            modifiers.append(part)
        else:
            if key_name is not None:
                raise ActionFailed(
                    f"Multiple non-modifier keys in hotkey '{combo_str}': "
                    f"'{key_name}' and '{part}'."
                )
            key_name = part

    if key_name is None:
        raise ActionFailed(f"No key found in hotkey '{combo_str}' (only modifiers).")

    keycode = KEYCODE_MAP.get(key_name)
    if keycode is None:
        raise ActionFailed(
            f"Unknown key '{key_name}' in hotkey '{combo_str}'. "
            f"Available: {sorted(KEYCODE_MAP.keys())}"
        )

    return keycode, modifiers


def press_hotkey(keycode: int, modifiers: list[str] | None = None) -> None:
    """Press a key with optional modifier keys.

    Args:
        keycode: The macOS virtual keycode.
        modifiers: List of modifier names (e.g. ["cmd", "shift"]).
    """
    if not QUARTZ_AVAILABLE:
        raise ActionFailed("Quartz not available for keyboard input.")

    flags = 0
    for mod in modifiers or []:
        flag = MODIFIER_MAP.get(mod.lower())
        if flag is None:
            raise ActionFailed(
                f"Unknown modifier '{mod}'. Available: {sorted(MODIFIER_MAP.keys())}"
            )
        flags |= flag

    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)

    if flags:
        CGEventSetFlags(down, flags)
        CGEventSetFlags(up, flags)

    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


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

    # Use keycode 0 as placeholder — CGEventKeyboardSetUnicodeString overrides
    down = CGEventCreateKeyboardEvent(None, 0, True)
    up = CGEventCreateKeyboardEvent(None, 0, False)

    from Quartz import CGEventKeyboardSetUnicodeString

    CGEventKeyboardSetUnicodeString(down, len(char), char)
    CGEventKeyboardSetUnicodeString(up, len(char), char)

    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)
