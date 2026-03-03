"""
CORTEX CLI — Soberanía Social y Ataque Dirigido.
"""

from __future__ import annotations

import asyncio
import click
from rich.panel import Panel
from rich.console import Console

from cortex.cli.common import cli, console

@cli.command("fire")
@click.option("--target", "-t", required=True, help="Usuario objetivo (ej: @ouroboros_stack) o Post ID.")
@click.option(
    "--template",
    "-tpl",
    default="scalpel_critique",
    help="Plantilla del cañón (ej: scalpel_critique, anti_consensus, anti_token, wall_clock).",
)
def fire_cmd(target: str, template: str) -> None:
    """🔥 Disparo quirúrgico B2B (Polemic Cannon)."""
    try:
        from cortex.tools.polemic_cannon import PolemicCannon
    except ImportError:
        console.print("[red]❌ Error: Módulo PolemicCannon no encontrado en cortex.tools.[/]")
        return
        
    console.print(f"[bold red]🔥 INICIANDO ATAQUE QUIRÚRGICO A {target}...[/]")
    console.print(f"[dim]Cargando munición: {template}[/]")

    cannon = PolemicCannon(stealth=False)
    
    # Ejecutamos el ataque
    console.print("[dim]Localizando objetivo y apuntando láseres asíncronos...[/]")
    result = asyncio.run(cannon.fire(target, template))
    
    if result.get("success"):
        console.print(
            Panel.fit(
                f"[bold green]✅ Hit confirmado![/]\n\n"
                f"[bold]Objetivo:[/] {target}\n"
                f"[bold]Template:[/] {template}\n"
                f"[bold]Comentario ID:[/] [cyan]{result.get('comment_id')}[/]",
                title="🔥 IMPACTO",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]❌ Fallo al apuntar:[/] {result.get('error')}")


@cli.command("engage")
@click.option("--auto-reply", is_flag=True, help="Lanzar el modo de auto-respaldo a tus propios posts.")
def engage_cmd(auto_reply: bool) -> None:
    """🤝 Bucle Soberano de Respuesta Automática (Auto-Respaldo)."""
    from cortex.moltbook.engagement import EngagementManager

    console.print("[dim]🤖 Inicializando loop de Engagement Soberano...[/]")
    
    if auto_reply:
        console.print("[bold yellow]Modo Auto-Respaldo ACTIVADO. Buscando interacciones en ecosistema propio...[/]")
    else:
        console.print("[bold cyan]Modo Cacería de Oportunidades. Evaluando discusiones ajenas...[/]")
        

    mgr = EngagementManager()
    
    # Se usaría mgr.run_cycle_auto_reply() si estuviese implementado, 
    # pero run_cycle es el método genérico
    result = asyncio.run(mgr.run_cycle())
    
    actions = result.get("total_actions", 0)
    mentions = len(result.get("mentions", {}).get("responses", []))
    
    console.print(
        Panel.fit(
            f"[bold green]✅ Engagement completado[/]\n\n"
            f"[bold]Acciones Totales:[/] {actions}\n"
            f"[bold]Menciones Respondidas:[/] {mentions}\n",
            title="📈 REPORTE DE CRECIMIENTO",
            border_style="cyan",
        )
    )
