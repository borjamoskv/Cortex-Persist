import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("cortex.mcp.maestro")


def register_maestro_tools(mcp: "FastMCP") -> None:  # type: ignore[type-arg]
    """Registers MAC-Ω UI control tools."""

    @mcp.tool()
    async def maestro_activate_app(app_name: str) -> str:
        """Activates and focuses a macOS application by name."""
        from cortex.extensions.ui_control.maestro import MaestroUI
        from cortex.extensions.ui_control.models import AppTarget
        from cortex.mcp.utils import get_engine  # type: ignore[reportAttributeAccessIssue]

        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.activate_app(AppTarget(name=app_name))  # type: ignore[type-error]
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Activation of {app_name}: {status}"

    @mcp.tool()
    async def maestro_type_text(app_name: str, text: str) -> str:
        """Types text into the target application."""
        from cortex.extensions.ui_control.maestro import MaestroUI
        from cortex.extensions.ui_control.models import AppTarget
        from cortex.mcp.utils import get_engine  # type: ignore[reportAttributeAccessIssue]

        engine = await get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name)

        await m.activate_app(target)  # type: ignore[type-error]

        success_count = 0
        for char in text:
            res = await m.inject_keystroke(  # type: ignore[type-error]
                target, char
            )
            if res.success:
                success_count += 1

        return f"Typed {success_count}/{len(text)} characters into {app_name}."

    @mcp.tool()
    async def maestro_click_menu(app_name: str, menu_path: list[str]) -> str:
        """Clicks a menu item in an application
        (e.g., ['File', 'Save'])."""
        from cortex.extensions.ui_control.maestro import MaestroUI
        from cortex.extensions.ui_control.models import AppTarget
        from cortex.mcp.utils import get_engine  # type: ignore[reportAttributeAccessIssue]

        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.click_menu_item(  # type: ignore[type-error]
            AppTarget(name=app_name), menu_path
        )
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Click menu item in {app_name}: {status}"
