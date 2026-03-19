#!/usr/bin/env python3
"""
KARDASHEV-SWARM II - Structural Collapse Demonstration.
Shows how an O(N) mass ingestion mission is collapsed into an O(1) Bridge.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel

from cortex.extensions.swarm.centauro_engine import CentauroEngine, Formation

console = Console()


async def main():
    console.print(
        Panel.fit(
            "[bold #CCFF00]KARDASHEV-SWARM II: STRUCTURAL COLLAPSE DEMO[/]\n"
            "[dim]Axiom Ω₂: Transforming O(N) missions into O(1) Architecture.[/]",
            border_style="#CCFF00",
        )
    )

    engine = CentauroEngine()

    # Define a mission that triggers Kardashev detection (O(N) keywords)
    mission = "Massive ingestion and structural audit of 500 frontier nodes for epistemic gaps"
    formation = Formation.KARDASHEV_II

    console.print(f"\n[bold]Mission:[/] [cyan]{mission}[/]")
    console.print(f"[bold]Formation:[/] [magenta]{formation}[/]")
    console.print("\n[yellow]Starting Swarm Engine...[/]")

    # Run the mission
    result = await engine.engage(mission, formation=formation)

    console.print("\n" + "=" * 60)
    console.print("[bold green]✅ PROTOCOL COMPLETE[/]")
    console.print(f"Status: [bold cyan]{result['status'].upper()}[/]")
    console.print(f"Solution/Bridge: [white]{result['solution']}[/]")
    console.print(f"Complexity Reduction: [bold #CCFF00]{result.get('reason', 'N/A')}[/]")
    console.print(f"Agents (Pseudo): [bold]{result.get('agents_used', 1)}[/]")
    console.print("=" * 60 + "\n")

    if result["status"] == "collapsed":
        console.print("[bold #CCFF00]SYNERGY DETECTED:[/] Complexity collapsed successfully.")
    else:
        console.print("[red]FAILURE:[/] Structural collapse failed.")


if __name__ == "__main__":
    asyncio.run(main())
