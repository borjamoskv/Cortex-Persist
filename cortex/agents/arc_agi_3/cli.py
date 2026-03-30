import asyncio
import json
import logging
from pathlib import Path
from queue import Queue

import click
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text

import cortex.agents.arc_agi_agent as _agent_reg  # noqa: F401 # Register CortexArcAgent
from cortex.agents.arc_agi_3.agent import ARCAgent
from cortex.agents.arc_agi_lib import AVAILABLE_AGENTS
from cortex.agents.arc_agi_agent import CortexArcAgent

# Ensure the agent is registered for Swarm
AVAILABLE_AGENTS["cortexarcagent"] = CortexArcAgent

console = Console()
logger = logging.getLogger("cortex.agents.arc_agi_3.cli")


class LimbicHandler(logging.Handler):
    """Bridges CORTEX limbic signals to the CLI UI."""

    def __init__(self, queue: Queue) -> None:
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.queue.put(msg)


def create_limbic_dashboard(step: str, status: str, thoughts: list[str]) -> Panel:
    """Creates a cinematic 'Industrial Noir' panel for ARC-AGI reasoning."""
    table = Table.grid(expand=True)
    table.add_row(f"[bold blue]Step:[/bold blue] {step}")
    table.add_row(f"[bold blue]Status:[/bold blue] {status}")
    table.add_row("")
    
    thought_text = Text()
    # Show last 5 thoughts
    start_idx = max(0, len(thoughts) - 5)
    for i in range(start_idx, len(thoughts)):
        thought_text.append(f"• {thoughts[i]}\n", style="italic cyan")
    
    table.add_row(Panel(thought_text, title="[dim]Thought Process[/dim]", border_style="dim"))

    return Panel(
        table,
        title="[bold white]CORTEX ARC-AGI V3[/bold white]",
        border_style="blue",
        padding=(1, 2)
    )


@click.group(name="arc3")
def arc_cli():
    """ARC-AGI-3 Sovereign Agent CLI."""
    pass


@arc_cli.command(name="solve")
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

    agent = ARCAgent()
    thought_queue = Queue()
    handler = LimbicHandler(thought_queue)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Attach to limbic logger (Ω3)
    limbic_logger = logging.getLogger("cortex.engine.limbic")
    limbic_logger.addHandler(handler)
    limbic_logger.setLevel(logging.INFO)

    console.print(Panel(
        f"Task: [bold]{task_file.name}[/bold]\nAX-046: JIT Concept Formation Active",
        title="[bold green]Sovereign Solver Loaded[/bold green]",
        border_style="green"
    ))

    thoughts = []

    # Run the async solver in the event loop
    try:
        with Live(
            create_limbic_dashboard("Synthesis", "Synthesizing PeARL Program...", thoughts),
            refresh_per_second=4,
        ) as live:
            
            async def run_and_track():
                task = asyncio.create_task(agent.run(task_data))
                while not task.done():
                    while not thought_queue.empty():
                        thoughts.append(thought_queue.get())
                    live.update(create_limbic_dashboard("Reasoning", "Exploring Program Space...", thoughts))
                    await asyncio.sleep(0.1)
                return await task

            from typing import Any, cast
            result = cast(list[list[int]], asyncio.run(run_and_track()))
            live.update(create_limbic_dashboard("Execution", "Applying Transformation to Grid...", thoughts))

        console.print("\n[bold green]✅ Prediction Generated[/bold green]")
        
        prog = agent.reasoning.active_program
        if prog and prog.confidence > 0.5:
            console.print(Panel(
                Text(prog.source_code, style="green"),
                title=f"[bold white]Crystallized Program (Conf: {prog.confidence:.2f})[/bold white]",
                border_style="white"
            ))

        console.print(f"Resulting Grid: {len(result)}x{len(result[0]) if result else 0}")

        # Show small preview if possible
        if result and len(result) <= 12 and len(result[0]) <= 12:
            for row in result:
                console.print(" ".join(str(c) for c in row))

    except Exception as e:
        console.print(f"[red]❌ Failure: {e}[/red]")
        logger.exception("CLI solve error")
    finally:
        limbic_logger.removeHandler(handler)


@arc_cli.command(name="run")
@click.option("--game", "-g", required=True, help="ARC game ID (e.g., ls20).")
@click.option(
    "--agent", "-a", default="cortexarcagent", help="Agent name (default: cortexarcagent)."
)
@click.option("--url", default="https://arcprize.org", help="Root URL for the ARC server.")
def run_cmd(game: str, agent: str, url: str):
    """Run an ARC game using the Swarm orchestrator."""
    from cortex.agents.arc_agi_lib import Swarm
    import cortex.agents.arc_agi_agent  # Register CortexArcAgent

    console.print(Panel(
        f"Game: [bold]{game}[/bold]\nAgent: [bold]{agent}[/bold]\n"
        "AX-044: Kinetic Intelligence Active",
        title="[bold blue]Sovereign Swarm Initializing[/bold blue]",
        border_style="blue"
    ))

    try:
        swarm = Swarm(agent=agent, games=[game], ROOT_URL=url)
        swarm.main()
        console.print("\n[bold green]✅ Swarm Execution Complete[/bold green]")
    except Exception as e:
        console.print(f"[red]❌ Swarm Failure: {e}[/red]")
        logger.exception("CLI run error")


if __name__ == "__main__":
    arc_cli()
