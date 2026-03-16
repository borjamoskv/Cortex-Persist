"""
CORTEX — Sovereign Window Management Engine for macOS.

Dedicated window operations: list, move, resize, minimize, fullscreen, close.
Uses AppleScript + System Events for maximum reliability across apps.
"""

import logging
from typing import TYPE_CHECKING, Optional

from cortex.ui_control.applescript import run_applescript
from cortex.ui_control.models import AppTarget, InteractionResult, WindowInfo

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.ui_control.window")


class WindowEngine:
    """
    Sovereign window management via AppleScript System Events.
    Handles listing, moving, resizing, minimizing, and fullscreen toggling.
    """

    def __init__(self, engine: Optional["CortexEngine"] = None) -> None:
        self.engine = engine

    async def list_windows(self, app_name: str) -> list[WindowInfo]:
        """
        Lists all windows for a given application.
        Returns structured WindowInfo objects with position, size, and state.
        """
        script = f"""
        tell application "System Events"
            tell process "{app_name}"
                set winCount to count of windows
                set resultList to ""
                repeat with i from 1 to winCount
                    set w to window i
                    set winName to name of w
                    set winPos to position of w
                    set winSize to size of w
                    set isMini to false
                    try
                        set isMini to value of attribute "AXMinimized" of w
                    end try
                    set resultList to resultList & winName & "|||" & ¬
                        (item 1 of winPos) & "," & (item 2 of winPos) & "|||" & ¬
                        (item 1 of winSize) & "," & (item 2 of winSize) & "|||" & ¬
                        isMini & "\\n"
                end repeat
                return resultList
            end tell
        end tell
        """

        try:
            output = await run_applescript(script, require_success=False)
            if not output:
                return []
            return self._parse_window_list(output, app_name)
        except Exception as e:
            logger.warning("Failed to list windows for %s: %s", app_name, e)
            return []

    def _parse_window_list(self, raw: str, app_name: str) -> list[WindowInfo]:
        """Parses pipe-delimited output from AppleScript into WindowInfo objects."""
        windows: list[WindowInfo] = []
        for i, line in enumerate(raw.strip().split("\n"), start=1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|||")
            if len(parts) < 4:
                continue
            try:
                pos = parts[1].split(",")
                size = parts[2].split(",")
                windows.append(
                    WindowInfo(
                        title=parts[0].strip(),
                        app_name=app_name,
                        x=int(pos[0].strip()),
                        y=int(pos[1].strip()),
                        width=int(size[0].strip()),
                        height=int(size[1].strip()),
                        minimized=parts[3].strip().lower() == "true",
                        index=i,
                    )
                )
            except (ValueError, IndexError):
                logger.debug("Skipping malformed window line: %s", line)
        return windows

    async def get_frontmost(self) -> WindowInfo | None:
        """Returns the frontmost window of the frontmost application."""
        script = """
        tell application "System Events"
            set frontApp to first process whose frontmost is true
            set appName to name of frontApp
            tell frontApp
                set win to window 1
                set winName to name of win
                set winPos to position of win
                set winSize to size of win
            end tell
            return appName & "|||" & winName & "|||" & ¬
                   (item 1 of winPos) & "," & (item 2 of winPos) & "|||" & ¬
                   (item 1 of winSize) & "," & (item 2 of winSize)
        end tell
        """
        try:
            output = await run_applescript(script, require_success=False)
            if not output:
                return None

            parts = output.split("|||")
            if len(parts) < 4:
                return None

            pos = parts[2].split(",")
            size = parts[3].split(",")
            return WindowInfo(
                title=parts[1].strip(),
                app_name=parts[0].strip(),
                x=int(pos[0].strip()),
                y=int(pos[1].strip()),
                width=int(size[0].strip()),
                height=int(size[1].strip()),
            )
        except Exception as e:
            logger.warning("Failed to get frontmost window: %s", e)
            return None

    async def move(self, target: AppTarget, x: int, y: int) -> InteractionResult:
        """Moves the frontmost window of the target app to (x, y)."""
        script = f"""
        tell application "{target.name}" to activate
        delay 0.3
        tell application "System Events"
            tell process "{target.name}"
                set position of window 1 to {{{x}, {y}}}
            end tell
        end tell
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def resize(self, target: AppTarget, width: int, height: int) -> InteractionResult:
        """Resizes the frontmost window of the target app."""
        script = f"""
        tell application "{target.name}" to activate
        delay 0.3
        tell application "System Events"
            tell process "{target.name}"
                set size of window 1 to {{{width}, {height}}}
            end tell
        end tell
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def minimize(self, target: AppTarget) -> InteractionResult:
        """Minimizes the frontmost window of the target app."""
        script = f"""
        tell application "{target.name}" to activate
        delay 0.2
        tell application "System Events"
            tell process "{target.name}"
                set value of attribute "AXMinimized" of window 1 to true
            end tell
        end tell
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def restore(self, target: AppTarget) -> InteractionResult:
        """Restores a minimized window."""
        script = f"""
        tell application "System Events"
            tell process "{target.name}"
                set value of attribute "AXMinimized" of window 1 to false
            end tell
        end tell
        tell application "{target.name}" to activate
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def fullscreen(self, target: AppTarget) -> InteractionResult:
        """Toggles fullscreen on the frontmost window of the target app."""
        script = f"""
        tell application "{target.name}" to activate
        delay 0.3
        tell application "System Events"
            tell process "{target.name}"
                set fsVal to value of attribute "AXFullScreen" of window 1
                set value of attribute "AXFullScreen" of window 1 to (not fsVal)
            end tell
        end tell
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))

    async def close_window(self, target: AppTarget) -> InteractionResult:
        """Closes the frontmost window of the target app via Cmd+W."""
        script = f"""
        tell application "{target.name}" to activate
        delay 0.2
        tell application "System Events"
            keystroke "w" using command down
        end tell
        """
        try:
            await run_applescript(script)
            return InteractionResult(success=True)
        except Exception as e:
            return InteractionResult(success=False, error=str(e))
