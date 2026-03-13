import asyncio

import click

from cortex.cli.common import console, get_engine
from cortex.ui_control.maestro import MaestroUI
from cortex.ui_control.models import AppTarget


@click.group(name="maestro")
def maestro():
    """MAC-Ω: Sovereign Desktop UI Automation (AppleScript/Native)."""
    pass


@maestro.command("activate")
@click.argument("app_name")
def activate_cmd(app_name: str):
    """Activate and focus a macOS application."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        res = await m.activate_app(AppTarget(name=app_name))
        if res.success:
            console.print(f"[green]✔ Successfully activated {app_name}[/green]")
        else:
            console.print(f"[red]✘ Failed to activate {app_name}: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("type")
@click.argument("app_name")
@click.argument("text")
def type_cmd(app_name: str, text: str):
    """Type text into the active window of the target application."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name)

        # Ensure focus first
        res = await m.activate_app(target)
        if not res.success:
            console.print(f"[red]✘ Failed to focus {app_name}: {res.error}[/red]")
            return

        await asyncio.sleep(0.5)

        console.print(f"Injecting {len(text)} characters into {app_name}...")
        for char in text:
            res = await m.inject_keystroke(target, char)
            if not res.success:
                msg = f"[red]✘ Failed at character '{char}': {res.error}[/red]"
                console.print(msg)
                return
            await asyncio.sleep(0.02)

        console.print("[green]✔ Done.[/green]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("click-menu")
@click.argument("app_name")
@click.argument("menu_path", nargs=-1)
def click_menu_cmd(app_name: str, menu_path: tuple[str, ...]):
    """
    Click a menu item.

    Example: cortex maestro click-menu Safari File "Export as PDF…"
    """

    async def _run():
        if len(menu_path) < 2:
            console.print("[red]✘ Menu path must have at least top-level menu and item.[/red]")
            return

        engine = get_engine()
        m = MaestroUI(engine=engine)
        target = AppTarget(name=app_name)
        res = await m.click_menu_item(target, list(menu_path))

        if res.success:
            path_str = " > ".join(menu_path)
            msg = f"[green]✔ Successfully clicked menu {path_str} in {app_name}[/green]"
            console.print(msg)
        else:
            console.print(f"[red]✘ Failed to click menu: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("click-id")
@click.argument("app_name")
@click.argument("identifier")
def click_id_cmd(app_name: str, identifier: str):
    """Click an element by its Accessibility Identifier."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        res = await m.click_element(app_name, identifier)

        if res.success:
            console.print(f"[green]✔ Successfully clicked {identifier} in {app_name}[/green]")
        else:
            console.print(f"[red]✘ Failed: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("click-at")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--button", default="left", help="left or right click")
def click_at_cmd(x: int, y: int, button: str):
    """Click at specific screen coordinates."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        res = await m.click_at(x, y, button)

        if res.success:
            console.print(f"[green]✔ Clicked at ({x}, {y})[/green]")
        else:
            console.print(f"[red]✘ Failed: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("scroll")
@click.argument("clicks", type=int)
def scroll_cmd(clicks: int):
    """Scroll the mouse wheel. Positive for up, negative for down."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        res = await m.scroll(clicks)

        if res.success:
            console.print(f"[green]✔ Scrolled {clicks} lines[/green]")
        else:
            console.print(f"[red]✘ Failed: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("capture")
@click.option("--x", type=int, help="Region start x")
@click.option("--y", type=int, help="Region start y")
@click.option("--w", type=int, help="Region width")
@click.option("--h", type=int, help="Region height")
def capture_cmd(x: int | None, y: int | None, w: int | None, h: int | None):
    """Capture a screenshot of the main display or a specific region."""

    async def _run():
        engine = get_engine()
        m = MaestroUI(engine=engine)
        region = (x, y, w, h) if all(v is not None for v in [x, y, w, h]) else None
        res = await m.capture(region)

        if res.success:
            console.print(f"[green]✔ Screenshot saved to: {res.output}[/green]")
        else:
            console.print(f"[red]✘ Failed: {res.error}[/red]")
        await engine.close()

    asyncio.run(_run())


@maestro.command("run")
@click.argument("instruction", nargs=-1)
def run_cmd(instruction: tuple[str, ...]):
    """Execute a natural language instruction using Mac Maestro (AppleScript)."""
    text = " ".join(instruction)

    async def _run():
        from cortex.agents.mac_maestro import MacMaestroAgent

        agent = MacMaestroAgent()
        console.print(f"Maestro Ω processing: '{text}'...")
        res = await agent.execute(text)

        if res.get("success"):
            console.print(f"[green]✔ Success: {res.get('explanation')}[/green]")
            if res.get("stdout"):
                console.print(res["stdout"])
        else:
            console.print(f"[red]✘ Failed: {res.get('error') or res.get('stderr')}[/red]")

    asyncio.run(_run())
