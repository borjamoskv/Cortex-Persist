"""
KETER-∞ Daemon CLI commands.
Sovereign Orchestration and Reality Weaver.
"""

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.core import _run_async
from cortex.engine.keter import KeterEngine
from cortex.errors import CortexError

console = Console()


@click.group(name="keter", help="👑 KETER-∞: El Botón de Dios (Orquestación Soberana).")
def keter_cmds() -> None:
    """Invoca la cascada fractal para construir ecosistemas."""
    pass


@keter_cmds.command("build")
@click.argument("intent", required=True)
def build_cmd(intent: str) -> None:
    """Construye un sistema completo desde cero."""
    console.print(Panel(f"[bold gold1]KETER-BUILD[/]\nIntención: {intent}", border_style="gold1"))

    engine = KeterEngine()
    try:
        result = _run_async(engine.ignite(intent))

        status = result.get("status", "UNKNOWN")
        console.print(f"\n[bold green]✓ KETER CASCADA COMPLETADA: {status}[/]")
    except CortexError as e:
        console.print(f"[bold red]Keter Error:[/] {e}")
        raise click.Abort() from e


@keter_cmds.command("rewrite")
@click.argument("target", required=True)
def rewrite_cmd(target: str) -> None:
    """Reescribe un componente de 0 a 100 sin preguntar."""
    console.print(
        Panel(f"[bold deep_pink4]KETER-REWRITE[/]\nTarget: {target}", border_style="deep_pink4")
    )

    engine = KeterEngine()
    try:
        _run_async(engine.ignite(f"Reescribe el componente {target} con estándar 130/100"))
        console.print("\n[bold green]✓ REESCRITURA COMPLETADA[/]")
    except CortexError as e:
        console.print(f"[bold red]Keter Error:[/] {e}")
        raise click.Abort() from e
