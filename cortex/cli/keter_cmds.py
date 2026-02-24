"""
KETER-∞ Daemon CLI commands.
Sovereign Orchestration and Reality Weaver.
"""

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.core import _run_async
from cortex.engine.keter import KeterEngine
from cortex.utils.errors import CortexError

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


@click.group(name="sovereign", help="⚡ SOVEREIGN: Orchestration and Biological Control.")
def sovereign_cmds() -> None:
    """Acceso directo al motor soberano de MOSKV-1."""
    pass


@sovereign_cmds.command("status")
def sovereign_status_cmd() -> None:
    """Muestra el estado del DigitalEndocrine y el PowerLevel."""
    from cortex.sovereign.endocrine import DigitalEndocrine
    from cortex.sovereign.observability import compute_power, Dimension

    endocrine = DigitalEndocrine()
    # Mocking dimension scores for status display
    scores = {dim.value: 100.0 for dim in Dimension}
    power = compute_power(scores, multiplier=1.3)

    console.print(Panel("[bold cyan]CORTEX SOVEREIGN STATUS[/]", border_style="cyan"))
    console.print(f"🌡️  [bold]Temp:[/][cyan] {endocrine.temperature:.2f}[/]")
    console.print(f"🎭  [bold]Style:[/][cyan] {endocrine.response_style}[/]")
    console.print(f"⚡  [bold]Power:[/][cyan] {power.power}/1000[/]")
    
    hormones = endocrine.to_dict()["hormones"]
    h_str = " | ".join([f"{k.capitalize()}: {v:.2f}" for k, v in hormones.items()])
    console.print(f"\n🧪 [dim]{h_str}[/]")


@sovereign_cmds.command("ignite")
@click.option("--env", default="production", help="Entorno de ejecución.")
def sovereign_ignite_cmd(env: str) -> None:
    """Ejecuta el pipeline soberano completo."""
    from cortex.sovereign.engine import run_pipeline

    console.print(Panel("[bold green]⚡ INICIANDO IGNICIÓN SOBERANA[/]", border_style="green"))
    
    try:
        ctx = _run_async(run_pipeline(environment=env))
        
        console.print("\n[bold]Fases del Pipeline:[/]")
        for r in ctx.results:
            status = "[green]✓[/]" if r.success else "[red]✗[/]"
            console.print(f"  {status} {r.phase.name:<20} [dim]{r.duration_ms:>8.1f}ms[/]")
            
        if ctx.power:
            console.print(f"\n[bold gold1]🌌 POWER LEVEL ALCANZADO: {ctx.power.power}[/]")
            if ctx.power.power >= 1300:
                console.print("[bold green]🏆 ESTADO SOBERANO VALIDADO[/]")

    except Exception as e:
        console.print(f"[bold red]Error de Ignición:[/] {e}")
        raise click.Abort() from e
