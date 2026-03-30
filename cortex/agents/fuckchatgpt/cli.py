import asyncio
import json
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from cortex.agents.fuckchatgpt.agent import FuckChatGPT

console = Console()
logger = logging.getLogger("cortex.agents.fuckchatgpt.cli")


def create_limbic_dashboard(step: str, status: str) -> Panel:
    """Creates a cinematic 'Industrial Noir' panel for ARC-AGI reasoning."""
    table = Table.grid(expand=True)
    table.add_row(f"[bold blue]Step:[/bold blue] {step}")
    table.add_row(f"[bold blue]Status:[/bold blue] {status}")
    
    return Panel(
        table,
        title="[bold white]CORTEX ARC-AGI V3[/bold white]",
        border_style="blue",
        padding=(1, 2)
    )


@click.group(name="fuckchatgpt")
def fuckchatgpt_cli():
    """FuckChatGPT Sovereign Agent CLI."""
    pass


@fuckchatgpt_cli.command(name="solve")
@click.argument("task_file", type=click.Path(exists=True, path_type=Path))
@click.option("--model", default="gemini-2.0-pro", help="Sovereign LLM for synthesis.")
def solve_cmd(task_file: Path, model: str):
    """Solve an ARC-AGI task using JIT synthesis."""
    try:
        with task_file.open("r", encoding="utf-8") as f:
            task_data = json.load(f)
    except Exception as e:
        console.print(f"[red]❌ Error loading task: {e}[/red]")
        return

    agent = FuckChatGPT()
    
    console.print(Panel(
        f"Task: [bold]{task_file.name}[/bold]\nAX-046: JIT Concept Formation Active",
        title="[bold green]Sovereign Solver Loaded[/bold green]",
        border_style="green"
    ))

    # Run the async solver in the event loop
    try:
        with Live(create_limbic_dashboard("Synthesis", "Synthesizing PeARL Program..."), refresh_per_second=4) as live:
            result = asyncio.run(agent.run(task_data))
            live.update(create_limbic_dashboard("Execution", "Applying Transformation to Grid..."))
            
        console.print("\n[bold green]✅ Prediction Generated[/bold green]")
        console.print(f"Resulting Grid: {len(result)}x{len(result[0]) if result else 0}")
        
        # Show small preview if possible
        if result and len(result) <= 10 and len(result[0]) <= 10:
            for row in result:
                console.print(" ".join(str(c) for c in row))
                
    except Exception as e:
        console.print(f"[red]❌ Failure: {e}[/red]")
        logger.exception("CLI solve error")


@fuckchatgpt_cli.command(name="compite")
@click.option("--game", "-g", default="ls20", help="ARC game ID (e.g., ls20).")
@click.option(
    "--agent", "-a", default="fuckchatgpt", help="Agent name."
)
@click.option("--url", default="https://arcprize.org", help="Root URL for the ARC server.")
def compite_cmd(game: str, agent: str, url: str):
    """Run an ARC game using the Swarm orchestrator to compete until leading."""
    from cortex.agents.arc_agi_lib import Swarm
    import cortex.agents.fuckchatgpt.agent  # Register FuckChatGPT
    
    console.print(Panel(
        f"Game: [bold]{game}[/bold]\nAgent: [bold]{agent}[/bold]\n"
        "AX-044: Kinetic Intelligence Active - Compitiendo hasta liderar",
        title="[bold blue]Sovereign Swarm Initializing[/bold blue]",
        border_style="blue"
    ))
    
    try:
        swarm = Swarm(agent=agent, games=[game], ROOT_URL=url)
        swarm.main()
        console.print("\n[bold green]✅ Swarm Execution Complete[/bold green]")
    except Exception as e:
        console.print(f"[red]❌ Swarm Failure: {e}[/red]")
        logger.exception("CLI compite error")

if __name__ == "__main__":
    fuckchatgpt_cli()
