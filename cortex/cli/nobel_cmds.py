import asyncio
import click
from cortex.cli.common import cli, console
from cortex.extensions.agents.nobel_swarm_mcts import launch_cortex_swarm_100

@cli.command("nobel-100")
@click.argument("problem", type=str, required=True)
def nobel_100_cmd(problem: str) -> None:
    """Ignite the NOBEL-Ω Swarm (MCTS AlphaZero self-play) on a mathematical/scientific problem."""
    console.print(f"[bold blue]CORTEX-SWARM-100[/] Igniting 100-agent topological assault on:\n[bold white]{problem}[/]")
    asyncio.run(launch_cortex_swarm_100(problem))
