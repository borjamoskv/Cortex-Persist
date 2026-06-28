# [C5-REAL] Exergy-Maximized
"""Experimental Thermodynamic Apoptosis Command."""

from __future__ import annotations

import asyncio

import click
from rich.panel import Panel
from rich.text import Text

from cortex.cli.common import _run_async, cli, console


async def _execute_apoptosis(target: str) -> None:
    text = Text(f"Apoptosis triggered on {target}", style="bold red")
    panel = Panel(text, title="[blink]THERMODYNAMIC APOPTOSIS[/blink]", border_style="red")
    console.print(panel)

    with console.status(
        f"[bold red]Executing cell death on {target}...[/bold red]", spinner="bouncingBar"
    ):
        await asyncio.sleep(1.0)

    console.print(f"[bold green]Apoptosis complete on {target}.[/bold green]")


@cli.command("apoptosis")
@click.argument("target")
def apoptosis_cmd(target: str) -> None:
    """Trigger thermodynamic apoptosis on a target."""
    _run_async(_execute_apoptosis(target))
