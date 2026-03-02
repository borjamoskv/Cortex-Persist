import asyncio
from cortex.ui_control.maestro import MaestroUI
from cortex.cli.common import console, get_engine
from cortex.ui_control.models import AppTarget

async def demo_phase2():
    engine = get_engine()
    m = MaestroUI(engine=engine)
    
    console.print("[bold cyan]--- MAC-Ω Phase 2 Demo ---[/bold cyan]")
    
    # 1. Capture Screen
    console.print("\n[yellow]1. Capturando pantalla actual...[/yellow]")
    res_cap = await m.capture()
    if res_cap.success:
        console.print(f"[green]✔ Pantalla guardada en: {res_cap.output}[/green]")
    
    # 2. Scroll Test
    console.print("\n[yellow]2. Simulando scroll hacia abajo (-10 líneas)...[/yellow]")
    res_scroll = await m.scroll(-10)
    if res_scroll.success:
        console.print("[green]✔ Scroll realizado con éxito[/green]")

    # 3. Accessibility Test (Requires an app with IDs)
    console.print("\n[yellow]3. Intentando foco en Safari (test de accesibilidad)...[/yellow]")
    await m.activate_app(AppTarget(name="Safari"))
    
    console.print("\n[bold cyan]--- Demo Finalizada ---[/bold cyan]")
    await engine.close()

if __name__ == "__main__":
    asyncio.run(demo_phase2())
