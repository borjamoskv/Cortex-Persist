# [C5-REAL] Exergy-Maximized

import asyncio

import click
from rich.console import Console
from rich.panel import Panel

from babylon60.cli.common import cli
from babylon60.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from babylon60.extensions.llm.provider import LLMProvider
from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.mcts.tree import MCTSEngine

console = Console()


@click.group(name="mcts")
def mcts_cmds() -> None:
    """CORTEX Chronos (Git-MCTS) - Búsqueda de Mutaciones Asintóticas."""


@mcts_cmds.command()
@click.option("--file", "-f", required=True, help="Target file to mutate.")
@click.option("--simulations", "-s", type=int, default=3, help="Max Monte Carlo iterations.")
@click.option(
    "--prompt",
    "-p",
    default="Optimize thermodynamics and ensure O(1) logic.",
    help="System mutation prompt.",
)
def evolve(file: str, simulations: int, prompt: str) -> None:
    """Evolve the given Python file mathematically via AlphaZero-autodidact."""
    try:
        console.print(
            Panel.fit(
                f"[bold magenta]🌌 EXERGY ENGINE STARTING MCTS[/bold magenta]\nTarget: [cyan]{file}[/cyan]",
                border_style="cyan",
            )
        )

        # Instanciar el enrutador soberano (P0 usa OpenAI GPT-5.4 o DeepSeek-v3 local)
        router = CortexLLMRouter(
            primary=LLMProvider(provider="ollama"),  # AlphaZero Local Synthesis
            db_path=DEFAULT_DB_PATH,
        )

        engine = MCTSEngine(target_file=file, router=router)

        # Ejecutar bucle cuántico en el event loop principal
        best_branch = asyncio.run(engine.run(max_iterations=simulations, mutation_str=prompt))

        if best_branch:
            console.print(
                f"\n[bold green]👑 MUTACIÓN CON ÉXITO - MCTS COLAPSADO: checkout a `{best_branch}`[/bold green]"
            )

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Singularity Error:[/red] {e}")
        raise click.Abort() from e


@mcts_cmds.command("prune")
def prune() -> None:
    """[LEA-OMEGA] Garbage Collect orphaned MCTS Chronos worktrees and branches."""
    from pathlib import Path

    from babylon60.mcts.git_env import MCTSGitEnvironment

    try:
        console.print(
            Panel.fit(
                "[bold red]🗑️  CHRONOS GC: Initiating Apoptosis[/bold red]", border_style="red"
            )
        )

        # We don't need a real router or target file for pruning, just any file in the repo
        env = MCTSGitEnvironment(router=None, target_file=Path(__file__))  # type: ignore

        metrics = asyncio.run(env.prune_orphans())

        console.print(f"[green]✔ Pruned Worktrees:[/green] {metrics['worktrees_removed']}")
        console.print(f"[green]✔ Pruned Branches:[/green] {metrics['branches_removed']}")

        if metrics["worktrees_removed"] == 0 and metrics["branches_removed"] == 0:
            console.print("[dim]The timeline is already clean. Zero anergy detected.[/dim]")

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Pruning Error:[/red] {e}")
        raise click.Abort() from e


cli.add_command(mcts_cmds)
