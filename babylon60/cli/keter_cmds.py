# [C5-REAL] Exergy-Maximized
"""
KETER-∞ Daemon CLI commands.
Sovereign Orchestration and Reality Weaver.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from babylon60.cli.common import _run_async, cli
from babylon60.engine.speculative.keter import KeterEngine
from babylon60.utils.errors import CortexError

console = Console()


@click.group(name="keter", help="👑 KETER-∞: The God Button (Sovereign Orchestration).")
def keter_cmds() -> None:
    """Invokes the fractal cascade to build ecosystems."""


@keter_cmds.command("build")
@click.argument("intent", required=True)
def build_cmd(intent: str) -> None:
    """Builds a complete system from scratch."""
    console.print(Panel(f"[bold gold1]KETER-BUILD[/]\nIntent: {intent}", border_style="gold1"))

    engine = KeterEngine()
    try:
        result = _run_async(engine.ignite(intent))

        status = result.get("status", "UNKNOWN")
        console.print(f"\n[bold green]✓ KETER CASCADE COMPLETED: {status}[/]")
    except CortexError as e:
        console.print(f"[bold red]Keter Error:[/] {e}")
        raise click.Abort() from e


@keter_cmds.command("rewrite")
@click.argument("target", required=True)
def rewrite_cmd(target: str) -> None:
    """Rewrites a component from 0 to 100 without asking."""
    console.print(
        Panel(f"[bold deep_pink4]KETER-REWRITE[/]\nTarget: {target}", border_style="deep_pink4")
    )

    engine = KeterEngine()
    try:
        _run_async(engine.ignite(f"Rewrite the {target} component with 130/100 standard"))
        console.print("\n[bold green]✓ REWRITE COMPLETED[/]")
    except CortexError as e:
        console.print(f"[bold red]Keter Error:[/] {e}")
        raise click.Abort() from e


@click.group(name="sovereign", help="⚡ SOVEREIGN: Orchestration and Biological Control.")
def sovereign_cmds() -> None:
    """Direct access to the MOSKV-1 sovereign engine."""


@sovereign_cmds.command("status")
def sovereign_status_cmd() -> None:
    """Displays the status of DigitalEndocrine and PowerLevel."""
    from babylon60.extensions.sovereign.endocrine import DigitalEndocrine
    from babylon60.extensions.sovereign.observability import Dimension, compute_power

    endocrine = DigitalEndocrine()
    # Mocking dimension scores for status display
    scores = {dim.value: 100.0 for dim in Dimension}
    power = compute_power(scores, multiplier=1.3)

    console.print(Panel("[bold cyan]CORTEX SOVEREIGN STATUS[/]", border_style="cyan"))
    console.print(f"🌡️  [bold]Temp:[/][cyan] {endocrine.get_temperature():.2f}[/]")
    console.print(f"🎭  [bold]Style:[/][cyan] {endocrine.get_response_style()}[/]")
    console.print(f"⚡  [bold]Power:[/][cyan] {power.power}/1000[/]")

    hormones = endocrine.to_dict()["hormones"]
    h_str = " | ".join([f"{k.capitalize()}: {v:.2f}" for k, v in hormones.items()])
    console.print(f"\n🧪 [dim]{h_str}[/]")


@sovereign_cmds.command("ignite")
@click.option("--env", default="production", help="Execution environment.")
def sovereign_ignite_cmd(env: str) -> None:
    """Executes the complete sovereign pipeline."""
    from babylon60.extensions.sovereign.engine import run_pipeline

    console.print(Panel("[bold green]⚡ STARTING SOVEREIGN IGNITION[/]", border_style="green"))

    try:
        ctx = _run_async(run_pipeline(environment=env))

        console.print("\n[bold]Pipeline Phases:[/]")
        for r in ctx.results:
            status = "[green]✓[/]" if r.success else "[red]✗[/]"
            console.print(f"  {status} {r.phase.name:<20} [dim]{r.duration_ms:>8.1f}ms[/]")

        if ctx.power:
            console.print(f"\n[bold gold1]🌌 POWER LEVEL REACHED: {ctx.power.power}[/]")
            if ctx.power.power >= 1300:
                console.print("[bold green]🏆 SOVEREIGN STATUS VALIDATED[/]")

    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]Ignition Error:[/] {e}")
        raise click.Abort() from e


cli.add_command(keter_cmds)
cli.add_command(sovereign_cmds)
