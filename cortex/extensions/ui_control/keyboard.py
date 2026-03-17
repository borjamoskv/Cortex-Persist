"""
CORTEX — Sovereign Keyboard Engine for macOS.

Dedicated keyboard automation: hotkeys, text input, special keys.
Uses AppleScript (System Events) for reliable keystroke injection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.extensions.ui_control.applescript import run_applescript
from cortex.extensions.ui_control.models import (
    SPECIAL_KEY_MAP,
    AppTarget,
    InteractionResult,
    KeyCombo,
)

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.ui_control.keyboard")

# Default inter-character delay (seconds) — human-like cadence
DEFAULT_TYPING_DELAY = 0.03


class KeyboardEngine:
    """
    Sovereign keyboard automation via AppleScript System Events.
    Handles hotkeys, text input, and special key sequences.
    """

    def __init__(self, engine: CortexEngine | None = None) -> None:
        self.engine = engine

    async def press(
        self,
        combo: KeyCombo,
        target: AppTarget | None = None,
    ) -> InteractionResult:
        """
        Press a key combination (optionally targeting a specific app).

        Args:
            combo: The key + modifiers to press.
            target: If provided, activates the app first.
        """
        action = combo.to_applescript()

        if target:
            script = f"""
            tell application "{target.name}" to activate
            delay 0.3
            tell application "System Events"
                {action}
            end tell
            """
        else:
            script = f"""
            tell application "System Events"
                {action}
            end tell
            """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def hotkey(
        self,
        key: str,
        *modifiers: str,
        target: AppTarget | None = None,
    ) -> InteractionResult:
        """
        Convenience method for pressing a hotkey combination.

        Examples:
            hotkey("s", "command")           -> Cmd+S
            hotkey("z", "command", "shift")  -> Shift+Cmd+Z
            hotkey("return")                 -> Enter
        """
        combo = KeyCombo(key=key, modifiers=list(modifiers))
        return await self.press(combo, target=target)

    async def type_text(
        self,
        text: str,
        target: AppTarget | None = None,
        delay: float = DEFAULT_TYPING_DELAY,
    ) -> InteractionResult:
        """
        Types text character by character with human-like cadence.

        For bulk text (>50 chars), uses clipboard injection for speed.
        Falls back to keystroke-per-character for short strings.
        """
        if not text:
            return InteractionResult(success=True)

        # For long text, use clipboard injection — O(1) instead of O(n)
        if len(text) > 50:
            return await self._type_via_clipboard(text, target)

        return await self._type_char_by_char(text, target, delay)

    async def _type_char_by_char(
        self,
        text: str,
        target: AppTarget | None,
        delay: float,
    ) -> InteractionResult:
        """Injects text one character at a time via AppleScript keystroke."""
        activate = ""
        if target:
            activate = f"""
            tell application "{target.name}" to activate
            delay 0.3
            """

        lines: list[str] = []
        for char in text:
            if char == "\n":
                lines.append("key code 36")
            elif char == "\t":
                lines.append("key code 48")
            else:
                escaped = char.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'keystroke "{escaped}"')
                lines.append(f"delay {delay}")

        keystrokes = "\n                ".join(lines)
        script = f"""
        {activate}
        tell application "System Events"
            {keystrokes}
        end tell
        """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def _type_via_clipboard(
        self,
        text: str,
        target: AppTarget | None,
    ) -> InteractionResult:
        """Uses clipboard paste for fast bulk text injection."""
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')

        activate = ""
        if target:
            activate = f"""
            tell application "{target.name}" to activate
            delay 0.3
            """

        script = f"""
        set the clipboard to "{escaped}"
        {activate}
        tell application "System Events"
            keystroke "v" using command down
        end tell
        """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def press_special(
        self,
        key_name: str,
        target: AppTarget | None = None,
    ) -> InteractionResult:
        """
        Press a special key by name (return, tab, escape, arrows, etc).
        """
        key_code = SPECIAL_KEY_MAP.get(key_name.lower())
        if key_code is None:
            valid = ", ".join(sorted(SPECIAL_KEY_MAP.keys()))
            return InteractionResult(
                success=False,
                error=f"Unknown special key: '{key_name}'. Valid keys: {valid}",
            )

        activate = ""
        if target:
            activate = f"""
            tell application "{target.name}" to activate
            delay 0.3
            """

        script = f"""
        {activate}
        tell application "System Events"
            key code {key_code}
        end tell
        """

        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))
