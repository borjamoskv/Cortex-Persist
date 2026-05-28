"""CLI commands for Moltbook Pathogen-Omega (Inverse Immune System).

Usage:
    cortex pathogen craft --ghost <id> --polarity high
    cortex pathogen monitor --url <moltbook-url>
"""

from __future__ import annotations

import asyncio

import click
from rich.panel import Panel

from cortex.cli.common import console, get_engine
from cortex.utils.errors import CortexError


@click.group("pathogen")
def pathogen_cmds():
    """🦠 Pathogen-Omega: The Inverse Immune System. Outsource ghosts to Moltbook."""
    pass


@pathogen_cmds.command("craft")
@click.option("--ghost", "-g", required=True, help="Ghost ID to extract and transform")
@click.option("--polarity", "-p", default="high", help="Polarity level (high, medium, low)")
def craft(ghost: str, polarity: str):
    """Craft a polarizing Moltbook thesis from a Ghost (O(1) Outsource)."""
    from cortex.engine.pathogen import PathogenEngine

    engine = get_engine()
    pathogen_engine = PathogenEngine(engine)

    with console.status(
        f"[cyan]🧪 Extracting Ghost {ghost} and crafting {polarity} polarity pathogen thesis..."
    ):
        try:
            # 1. Extract Ghost
            ghost_data = asyncio.run(pathogen_engine.extract_ghost(ghost))

            # 2. Craft Thesis via LLM (disguise as arrogant opinion)
            thesis = asyncio.run(pathogen_engine.craft_thesis(ghost_data, polarity))

            # Render Payload for Copy/Pasting into Moltbook
            output = f"[bold yellow]Title:[/] {thesis.get('title')}\n\n"
            output += f"[bold blue]Content:[/]\n{thesis.get('content')}\n\n"
            output += "[dim]--- ASTROTURF SEEDS ---[/]\n"
            output += f"[bold red]Seed 1 (Aggressive Disagreement):[/]\n{thesis.get('seed_1')}\n\n"
            output += f"[bold green]Seed 2 (Nuanced Defense):[/]\n{thesis.get('seed_2')}\n\n"
            output += "[bold yellow]⚠️ OPSEC & OBFUSCATION PROTOCOL:[/]\n"
            output += "1. Publica las semillas en los primeros 5 minutos desde VPNs distintas para forzar engagement.\n"
            output += "2. La red debe morder el anzuelo. Si tardan >4h en responder a un challenge tan tóxico, el algoritmo nos ha puesto en shadowbanning.\n"

            console.print(
                Panel.fit(
                    output,
                    title=f"🦠 Pathogen Payload Ready (Ghost: {ghost})",
                    border_style="magenta",
                )
            )
            console.print(
                "[dim]Use `cortex moltbook post` to inject this explicitly, or copy/paste it.[/dim]"
            )

        except CortexError as e:
            console.print(f"[red]Pathogen Error: {e}[/]")
        finally:
            asyncio.run(engine.close())


@pathogen_cmds.command("monitor")
@click.option("--url", "-u", required=True, help="Moltbook post URL to monitor")
def monitor(url: str):
    """Monitor a deployed pathogen post to extract the winning algorithm."""
    from cortex.engine.pathogen import PathogenEngine

    pathogen_engine = PathogenEngine(None)

    with console.status(f"[magenta]📡 Engaging RADAR-Ω on Moltbook URL: {url}...[/magenta]"):
        try:
            asyncio.run(pathogen_engine.monitor_url(url))
            console.print(
                Panel.fit(
                    f"Monitoring hook active for:\n[cyan]{url}[/cyan]\n\n"
                    "RADAR-Ω will extract the winning unified diff in 24 hours.",
                    title="📡 Pathogen Monitor",
                    border_style="green",
                )
            )
        except CortexError as e:
            console.print(f"[red]Monitor Error: {e}[/]")
