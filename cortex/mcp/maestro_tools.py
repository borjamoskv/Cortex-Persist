from typing import Optional

from mcp.server.fastmcp import FastMCP

from cortex.extensions.ui_control.maestro import MaestroUI
from cortex.extensions.ui_control.models import AppTarget
from cortex.mcp.utils import get_engine  # type: ignore[reportAttributeAccessIssue]


def register_maestro_tools(mcp: FastMCP):
    """Registers MAC-Ω UI control tools."""

    @mcp.tool()
    async def maestro_activate_app(app_name: str) -> str:
        """Activates and focuses a macOS application by name."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.activate_app(AppTarget(name=app_name))
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Activation of {app_name}: {status}"

    @mcp.tool()
    async def maestro_type_text(app_name: str, text: str) -> str:
        """Types text into the target application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name)
        await m.activate_app(target)
        res = await m.type_text(text, target=target)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Type text into {app_name}: {status}"

    @mcp.tool()
    async def maestro_click_menu(app_name: str, menu_path: list[str]) -> str:
        """Clicks a menu item in an application (e.g., ['File', 'Save'])."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.click_menu_item(AppTarget(name=app_name), menu_path)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Click menu item in {app_name}: {status}"

    @mcp.tool()
    async def maestro_inspect(app_name: str, depth: int = 5) -> str:
        """Dumps the accessibility (AX) tree of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        tree = m.dump_tree(app_name, max_depth=depth)
        if not tree:
            return f"No AX elements found for '{app_name}' or app is not running."

        lines = [f"AX Tree for {app_name}:"]
        for el in tree:
            indent = "  " * (el.depth or 0)
            role = el.role or "?"
            title = f' "{el.title}"' if el.title else ""
            ident = f" [{el.identifier}]" if el.identifier else ""
            lines.append(f"{indent}{role}{title}{ident}")
        return "\n".join(lines)

    @mcp.tool()
    async def maestro_find_element(app_name: str, query: str, by: str = "title") -> str:
        """Search AX elements by title, role, or identifier."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        results = []
        if by == "title":
            el = m.find_element_by_title(app_name, query)
            if el:
                results.append(el)
        elif by == "role":
            results = m.find_elements_by_role(app_name, query)
        else:
            el = m.find_element(app_name, query)
            if el:
                results.append(el)

        if not results:
            return f"No results for '{query}' by {by} in {app_name}."

        lines = [f"Found {len(results)} elements:"]
        for el in results:
            name = el.title or el.identifier or "(no name)"
            lines.append(f"  - {el.role}: {name}")
        return "\n".join(lines)

    @mcp.tool()
    async def maestro_hotkey(key: str, modifiers: list[str], app_name: Optional[str] = None) -> str:
        """Sends a keyboard shortcut (e.g., key='c', modifiers=['command'])."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name) if app_name else None
        res = await m.hotkey(key, *modifiers, target=target)
        status = "Success" if res.success else f"Failed: {res.error}"
        label = app_name or "frontmost"
        return f"Hotkey {'+'.join(modifiers)}+{key} in {label}: {status}"

    @mcp.tool()
    async def maestro_mouse_click(x: int, y: int, button: str = "left") -> str:
        """Clicks at screen coordinates."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = m.click(x, y, button)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Mouse click {button} at ({x}, {y}): {status}"

    @mcp.tool()
    async def maestro_mouse_double_click(x: int, y: int) -> str:
        """Double clicks at screen coordinates."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = m.double_click(x, y)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Mouse double click at ({x}, {y}): {status}"

    @mcp.tool()
    async def maestro_mouse_drag(
        from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5
    ) -> str:
        """Drags from one point to another."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = m.drag(from_x, from_y, to_x, to_y, duration=duration)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Mouse drag ({from_x},{from_y}) -> ({to_x},{to_y}): {status}"

    @mcp.tool()
    async def maestro_mouse_scroll(clicks: int) -> str:
        """Scrolls the mouse wheel. Positive=up, Negative=down."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = m.scroll(clicks)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Mouse scroll {clicks} lines: {status}"

    @mcp.tool()
    async def maestro_move_window(app_name: str, x: int, y: int) -> str:
        """Moves the main window of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.move_window(AppTarget(name=app_name), x, y)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Move {app_name} window to ({x}, {y}): {status}"

    @mcp.tool()
    async def maestro_resize_window(app_name: str, width: int, height: int) -> str:
        """Resizes the main window of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.resize_window(AppTarget(name=app_name), width, height)
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Resize {app_name} window to {width}x{height}: {status}"

    @mcp.tool()
    async def maestro_minimize_window(app_name: str) -> str:
        """Minimizes the main window of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.minimize_window(AppTarget(name=app_name))
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Minimize {app_name} window: {status}"

    @mcp.tool()
    async def maestro_fullscreen_window(app_name: str) -> str:
        """Toggles fullscreen for the main window of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        res = await m.fullscreen_window(AppTarget(name=app_name))
        status = "Success" if res.success else f"Failed: {res.error}"
        return f"Toggle fullscreen for {app_name}: {status}"

    @mcp.tool()
    async def maestro_window_list(app_name: str) -> str:
        """Lists all windows of an application."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        windows = await m.list_windows(app_name)
        if not windows:
            return f"No windows found for '{app_name}' or app is not running."

        lines = [f"{app_name} Windows:"]
        for w in windows:
            state = " [minimized]" if w.minimized else ""
            if w.fullscreen:
                state = " [fullscreen]"
            info = f"'{w.title}' - {w.width}x{w.height} @ ({w.x},{w.y}){state}"
            lines.append(f"  • {info}")
        return "\n".join(lines)

    @mcp.tool()
    async def maestro_capture(output_path: Optional[str] = None) -> str:
        """Captures a screenshot of the primary display."""
        engine = await get_engine()
        m = MaestroUI(engine=engine)
        path = await m.screenshot(output_path)
        if path:
            return f"Screenshot saved to: {path}"
        return "Failed to capture screenshot."

    @mcp.tool()
    async def maestro_run_natural(instruction: str) -> str:
        """Executes a natural language instruction (e.g., 'open TextEdit and type hello')."""
        from cortex.extensions.agents.mac_maestro import MacMaestroAgent

        agent = MacMaestroAgent()
        res = await agent.execute(instruction)
        if res.get("success"):
            explanation = res.get("explanation", "Action completed")
            return f"Success: {explanation}"
        return f"Failed: {res.get('error') or res.get('stderr', 'Unknown error')}"
