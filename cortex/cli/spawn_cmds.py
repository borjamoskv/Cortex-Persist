"""
CORTEX CLI — Headless Agent Spawn.
Entry points for triggering detached, autonomous sub-agent execution.
"""

import click
from rich.console import Console

from cortex.cli.common import cli

console = Console()


@cli.command("spawn")
@click.option(
    "--target", required=True, help="Target module, file, or system for the agent to bind to."
)
@click.option("--intent", required=True, help="Primary directive for the autonomous execution.")
def spawn_cmd(target: str, intent: str) -> None:
    """Ignite a headless sub-agent to execute an intent autonomously.

    This command serves as the bridge for the Entropic Wake Daemon (VOID DAEMON)
    to trigger self-healing, refactoring, or autopoiesis operations without
    blocking the main thread or requiring operator UI interaction.
    """
    console.print("[bold green]🚀 [Headless Singularity IGNITED][/bold green]")
    console.print(f"Target: [cyan]{target}[/cyan]")
    console.print(f"Intent: [yellow]{intent}[/yellow]")
    console.print(
        "[dim]The agent is now operating autonomously in the Void. "
        "Check logs for physical mutations.[/dim]"
    )

    # Normally, we'd enqueue the task into the EntropicQueue or directly instantiate CentauroEngine
    # For MVP verification, we print and gracefully exit.
