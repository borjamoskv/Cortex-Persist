"""
CLI commands for Demiurge Omega (Sortu).
Dynamically forge and execute skills.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.syntax import Syntax

from cortex.cli.common import _run_async, cli, console
from cortex.extensions.evolution.demiurge import DemiurgeCompiler


@cli.group(name="demiurge")
def demiurge_group() -> None:
    """Demiurge Omega: Sovereign JIT Skill Compiler."""
    pass


@demiurge_group.command(name="forge")
@click.argument("intent", nargs=-1)
def forge(intent: tuple[str, ...]) -> None:
    """Dynamically compile, execute, and evaluate a skill."""
    if not intent:
        console.print('[red]✗ Missing intent.[/red] Usage: cortex demiurge forge "do something"')
        return

    intent_str = " ".join(intent)
    console.print(f"[bold cyan]⚒ Demiurge Omega Forge Initiated[/bold cyan] » '{intent_str}'")

    async def _run_forge():
        compiler = DemiurgeCompiler()
        return await compiler.forge_skill(intent_str)

    result = _run_async(_run_forge())

    if result["status"] == "SUCCESS":
        console.print(
            Panel(
                Syntax(result.get("code", ""), "python", theme="monokai"),
                title="[green]Forged Skill[/green]",
            )
        )
        console.print(
            f"[bold green]✓ Execution Success[/bold green] (Utility: {result.get('utility', 0.0)})"
        )
        console.print(f"Result: {result.get('result')}")
    else:
        console.print(f"[bold red]✗ Forge Failed: {result.get('reason')}[/bold red]")
        if "code" in result:
            console.print(
                Panel(
                    Syntax(result["code"], "python", theme="monokai"),
                    title="[red]Failed Code[/red]",
                )
            )
