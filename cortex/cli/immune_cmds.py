import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.common import cli, get_engine
from cortex.extensions.immune.breaker import (
    EpistemicState,
    evaluate_circuit_breaker,
    execute_circuit_trip,
)

console = Console()


@cli.group("immune")
def immune_group():
    """Immune system and epistemic membrane commands."""
    pass


@immune_group.command("circuit-breaker")
@click.option("--test-failures", default=0, help="Number of consecutive test failures")
@click.option("--unresolved-ghosts", default=0, help="Number of unresolved ghosts")
@click.option("--linting-mutations", default=0, help="Number of recent linting mutations")
@click.option("--reason", default="Manual invocation", help="Reason for the query")
def circuit_breaker_cmd(
    test_failures: int, unresolved_ghosts: int, linting_mutations: int, reason: str
):
    """
    Evaluate the cognitive entropy density and trip the Sovereign Lock if it exceeds the threshold.
    Also aliased as `/circuit-breaker`.
    """
    state = EpistemicState(
        consecutive_test_failures=test_failures,
        unresolved_ghosts=unresolved_ghosts,
        recent_linting_mutations=linting_mutations,
    )

    evaluation = evaluate_circuit_breaker(state)
    ed_score = evaluation["ed_score"]

    if evaluation["action"] == "TRIP_BREAKER":
        console.print(
            Panel.fit(
                f"[bold red]EPISTEMIC CIRCUIT BREAKER TRIPPED[/bold red]\n"
                f"Entropy Density: {ed_score:.1f}\n"
                f"Reason: {evaluation['reason']}",
                title="Singularity Event",
                border_style="red",
            )
        )

        cortex_engine = get_engine()
        import asyncio

        result = asyncio.run(execute_circuit_trip(reason, cortex_engine))

        console.print(f"[bold yellow]Result:[/bold yellow] {result}")
        console.print(
            "[bold red]SYSTEM LOCKED: Write access denied pending Sovereign Lock release.[/bold red]"
        )
    else:
        console.print(
            Panel.fit(
                f"[bold green]SYSTEM NOMINAL[/bold green]\n"
                f"Entropy Density: {ed_score:.1f} (Threshold: 50.0)\n"
                f"Reason: System is not thrashing.",
                title="Epistemic State",
                border_style="green",
            )
        )
