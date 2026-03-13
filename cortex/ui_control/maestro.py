import logging
from typing import TYPE_CHECKING, Any

from cortex.ui_control.applescript import is_app_running, run_applescript
from cortex.ui_control.accessibility import AccessibilityEngine
from cortex.ui_control.mouse import MouseEngine
from cortex.ui_control.vision import VisionEngine
from cortex.ui_control.models import AppTarget, InteractionResult
if TYPE_CHECKING:
    from cortex.engine import CortexEngine
else:
    CortexEngine = Any

logger = logging.getLogger("cortex.ui_control.maestro")


class MaestroUI:
    """
    Sovereign Desktop UI Automation Coordinator.
    Provides predictable, AppleScript-backed automation.
    Integrates with CORTEX Master Ledger for audit trails.
    """

    def __init__(self, engine: CortexEngine | None = None) -> None:
        self.engine = engine
        self.acc = AccessibilityEngine(engine=engine)
        self.mouse = MouseEngine(engine=engine)
        self.vision = VisionEngine(engine=engine)

    async def _persist_interaction(
        self, action: str, target: AppTarget, result: InteractionResult
    ) -> None:
        """Stores the UI interaction in the CORTEX Ledger."""
        if not self.engine:
            return

        content = f"MAC-Ω UI Interaction: {action} on {target.name}. Success: {result.success}"
        if not result.success:
            content += f" | Error: {result.error}"

        await self.engine.store(
            project="MAESTRO-Ω",
            content=content,
            fact_type="decision" if result.success else "error",
            tags=["ui_control", "macos", target.name.lower()],
            meta={
                "action": action,
                "app": target.name,
                "bundle_id": target.bundle_id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }
        )

    async def activate_app(self, target: AppTarget) -> InteractionResult:
        """Activates and brings the target application to the front."""
        script = f'tell application "{target.name}" to activate'
        try:
            await run_applescript(script)
            res = InteractionResult(success=True)
        except Exception as e:
            res = InteractionResult(success=False, error=str(e))

        await self._persist_interaction("activate_app", target, res)
        return res

    async def verify_app_state(self, target: AppTarget) -> bool:
        """Verifies if the application is running."""
        return await is_app_running(target.name)

    async def inject_keystroke(
        self, target: AppTarget, keystroke: str, modifiers: list[str] | None = None
    ) -> InteractionResult:
        """
        Injects a keystroke into the target application.

        Args:
            target: The app to focus before sending keys.
            keystroke: The key to press (e.g., "v", "return").
            modifiers: List of modifiers (e.g., ["command down", "shift down"]).
        """
        # Ensure focus first (Axiom 2: Absolute Intent)
        running = await self.verify_app_state(target)
        if not running:
            return InteractionResult(
                success=False, error=f"Cannot inject keystroke: {target.name} is not running."
            )

        mods_str = ""
        if modifiers:
            mods_str = f" using {{{', '.join(modifiers)}}}"

        # If keystroke is more than one character and uses "return", "tab", etc.
        # AppleScript uses bare words for special keys but strings for literals.
        # We need to format the script accordingly.
        script = f"""
        tell application "{target.name}" to activate
        delay 0.5
        tell application "System Events"
            keystroke "{keystroke}"{mods_str}
        end tell
        """
        # Note: delay 0.5 is added to ensure app activation completes before keystroke.

        try:
            await run_applescript(script)
            res = InteractionResult(success=True)
        except Exception as e:
            res = InteractionResult(success=False, error=str(e))

        await self._persist_interaction("inject_keystroke", target, res)
        return res

    async def click_menu_item(self, target: AppTarget, menu_path: list[str]) -> InteractionResult:
        """
        Clicks a specific menu item.

        Args:
            target: The application target.
            menu_path: E.g., ["File", "Export as PDF..."]
        """
        if len(menu_path) < 2:
            return InteractionResult(
                success=False, error="Menu path must have at least top-level menu and item"
            )

        script = f"""
        tell application "{target.name}" to activate
        tell application "System Events"
            tell process "{target.name}"
                click menu item "{menu_path[1]}" of menu "{menu_path[0]}" \
                    of menu bar item "{menu_path[0]}" of menu bar 1
            end tell
        end tell
        """

        try:
            await run_applescript(script)
            res = InteractionResult(success=True)
        except Exception as e:
            res = InteractionResult(success=False, error=str(e))

        await self._persist_interaction("click_menu_item", target, res)
        return res

    async def click_element(self, app_name: str, identifier: str) -> InteractionResult:
        """Clicks an element by its Accessibility Identifier."""
        element = self.acc.find_element(app_name, identifier)
        if not element:
            res = InteractionResult(
                success=False, error=f"Element with ID {identifier} not found in {app_name}"
            )
        else:
            res = await self.acc.perform_click(element)

        await self._persist_interaction("click_element", AppTarget(name=app_name), res)
        return res

    async def click_at(self, x: int, y: int, button: str = "left") -> InteractionResult:
        """Clicks at specific screen coordinates."""
        res = self.mouse.click(x, y, button)
        await self._persist_interaction("click_at", AppTarget(name="System"), res)
        return res

    async def scroll(self, clicks: int) -> InteractionResult:
        """Scrolls the mouse wheel."""
        res = self.mouse.scroll(clicks)
        await self._persist_interaction("scroll", AppTarget(name="System"), res)
        return res

    async def capture(self, region: tuple[int, int, int, int] | None = None) -> InteractionResult:
        """Captures a screenshot for visual verification."""
        res = self.vision.capture_screen(region)
        await self._persist_interaction("capture", AppTarget(name="System"), res)
        return res
