"""CORTEX v12.2 — SONIC-SWARM-Ω CLI.

Sovereign CLI wrapper for the x100 Yield generative music orchestrator.
Direct CDP + Swarm-10k scaling for Text-To-MIDI vectors.
"""

from __future__ import annotations

import asyncio
import logging

import click
from rich.console import Console

from cortex.cli.common import cli

logger = logging.getLogger("cortex.cli.sonic")
console = Console()

@click.group("sonic")
def sonic_cmds() -> None:
    """SONIC-SWARM-Ω Engine — cortex sonic <subcommand>."""
    pass

@sonic_cmds.command("ttm")
@click.argument("prompt", type=str)
@click.option("--tensions", default="0.1,0.5,0.9", help="Comma separated tension values to interpolate.")
def generate_ttm(prompt: str, tensions: str) -> None:
    """Run parallel x100 Text-to-MIDI generation using LEGION-10k and CDP."""
    tension_list = [float(t.strip()) for t in tensions.split(",") if t.strip()]
    asyncio.run(_run_ttm_grid(prompt, tension_list))

async def _run_ttm_grid(prompt: str, tension_list: list[float]) -> None:
    try:
        from cortex.extensions.swarm.sonic_swarm import SonicSwarmOrchestrator
    except ImportError as e:
        console.print(f"[red]Failed to load SONIC-SWARM-Ω engine: {e}[/]")
        return

    orchestrator = SonicSwarmOrchestrator()
    
    with console.status(f"[noir.violet]Forging [bold]{len(tension_list)}[/] semantic vectors for '{prompt}'...[/]"):
        try:
            results = await orchestrator.dispatch_ttm_grid(prompt, tension_list)
        finally:
            await orchestrator.annihilate()

    console.print(f"[[noir.cyber]✓[/]] [bold green]FORGE SUCCESS:[/] Generated {len(results)} MIDI vectors.")
    for res in results:
        console.print(f"  ↳ {res}")

cli.add_command(sonic_cmds)
