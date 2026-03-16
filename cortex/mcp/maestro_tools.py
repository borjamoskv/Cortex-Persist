import logging

from mcp.server.fastmcp import FastMCP

from cortex.mcp.utils import get_engine  # type: ignore[reportAttributeAccessIssue]
from cortex.ui_control.maestro import MaestroUI
from cortex.ui_control.models import AppTarget

logger = logging.getLogger("cortex.mcp.maestro")


def register_maestro_tools(mcp: FastMCP):
    """Registers MAC-Ω UI control tools."""

    @mcp.tool()
    async def maestro_activate_app(app_name: str) -> str:
        """Activates and focuses a macOS application by name."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.activate_app(AppTarget(name=app_name))  # type: ignore[type-error]
        return f"Activation of {app_name}: {'Success' if res.success else f'Failed: {res.error}'}"

    @mcp.tool()
    async def maestro_type_text(app_name: str, text: str) -> str:
        """Types text into the target application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name)

        # Focus first
        await m.activate_app(target)  # type: ignore[type-error]

        success_count = 0
        for char in text:
            res = await m.inject_keystroke(target, char)  # type: ignore[type-error]
            if res.success:
                success_count += 1

        return f"Typed {success_count}/{len(text)} characters into {app_name}."

    @mcp.tool()
    async def maestro_click_menu(app_name: str, menu_path: list[str]) -> str:
        """Clicks a menu item in an application (e.g., ['File', 'Save'])."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.click_menu_item(AppTarget(name=app_name), menu_path)  # type: ignore[type-error]
        return (
            f"Click menu item in {app_name}: {'Success' if res.success else f'Failed: {res.error}'}"
        )
