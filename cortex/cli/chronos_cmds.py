from typing import Optional

"""
Commands for CHRONOS-1 The Senior Benchmark.

Exposes the native API to calculate Human vs AI asymmetry.
"""

import click
from rich.console import Console
from rich.panel import Panel

from cortex.config import DEFAULT_DB_PATH
from cortex.extensions.timing.chronos import ChronosEngine

__all__ = ["chronos_cmds", "analyze", "compound", "projection"]

console = Console()


@click.group(name="chronos")
def chronos_cmds() -> None:
    """CHRONOS-1 — Benchmark of Senior Human Time vs AI Swarm Time."""
    pass


@chronos_cmds.command()
@click.option(
    "--ai-time",
    "-t",
    type=float,
    required=True,
    help="Time it took the AI swarm to complete the task (in seconds).",
)
@click.option(
    "--complexity",
    "-c",
    type=click.Choice(["low", "medium", "high", "god"], case_sensitive=False),
    default="medium",
    help="Task complexity multiplier level.",
)
def analyze(ai_time: float, complexity: str) -> None:
    """
    Analyzes the task asymmetry. Example:
    cortex chronos analyze --ai-time 120 --complexity high
    """
    try:
        metrics = ChronosEngine.analyze(ai_time, complexity)

        # Formatting
        human_time_str = ChronosEngine.format_time(metrics.human_time_secs)
        ai_time_str = ChronosEngine.format_time(metrics.ai_time_secs)

        content = (
            f"\n[cyan]⏱️  Human Senior Time:  [/cyan][white]{human_time_str}[/white]\n"
            f"[magenta]⚡ MOSKV Swarm Time:   [/magenta][white]{ai_time_str}[/white]\n"
            f"[green]🌌 Tactical Asymmetry: [/green][bold white]{metrics.asymmetry_factor}x[/bold white]\n\n"
            f"[dim]{metrics.context_msg}[/dim]\n\n"
            f"💡 [bold yellow]{metrics.tip}[/bold yellow]\n"
            f"⚠️  [dim red]{metrics.anti_tip}[/dim red]"
        )

        panel = Panel(
            content,
            title="[bold magenta]🕒 CHRONOS-1 — SENIOR BENCHMARK[/bold magenta]",
            border_style="magenta",
            expand=False,
        )

        console.print(panel)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@chronos_cmds.command()
@click.option(
    "--project",
    "-p",
    type=str,
    default=None,
    help="Filter by specific project (optional).",
)
@click.option(
    "--persist",
    is_flag=True,
    help="Persist report into CORTEX ledger.",
)
def compound(project: Optional[str], persist: bool) -> None:
    """Detect compound causal chains and report exponential Ω₁₁ yield."""
    from rich.table import Table

    from cortex.engine.compound_yield import CompoundYieldTracker

    try:
        tracker = CompoundYieldTracker(db_path=str(DEFAULT_DB_PATH))
        report = tracker.analyze_chains(project=project)

        table = Table(title=f"CHRONOS-1 Ω₁₁ Compound Chains (Project: {project or 'Global'})")
        table.add_column("Rank", justify="right", style="cyan", no_wrap=True)
        table.add_column("Root Fact ID", justify="right", style="magenta")
        table.add_column("Depth", justify="right", style="green")
        table.add_column("Chain Size", justify="right", style="blue")
        table.add_column("Linear (H)", justify="right")
        table.add_column("Compound (H)", justify="right", style="bold yellow")

        for idx, chain in enumerate(report.chains[:15], start=1):
            table.add_row(
                str(idx),
                f"#{chain.root_fact_id}",
                str(chain.depth),
                str(len(chain.fact_ids)),
                f"{chain.linear_hours:,.2f}",
                f"{chain.compound_hours:,.2f}",
            )

        console.print(table)

        summary = (
            f"\n[cyan]Total Linear (ΣH):[/cyan] [white]{report.total_linear:,.2f}h[/white]\n"
            f"[magenta]Total Compound (∏H):[/magenta] [bold yellow]{report.total_compound:,.2f}h[/bold yellow]\n"
            f"[green]Yield Multiplier:[/green] [bold white]{report.multiplier:.2f}x[/bold white]\n"
        )
        console.print(
            Panel(summary, title="[bold cyan]Ω₁₁ Axiom Summary[/bold cyan]", expand=False)
        )

        if persist:
            fact_id = tracker.persist_report(report, project=project or "system")
            if fact_id:
                console.print(f"[green]✔ Report persisted as Fact #{fact_id}[/green]")

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@chronos_cmds.command()
@click.option("--years", "-y", type=int, default=10, help="Number of years to project.")
@click.option("--base-hours", "-b", type=float, default=5000.0, help="Base linear hours / year.")
@click.option("--rate", "-r", type=float, default=0.15, help="Compound reuse rate (default 0.15).")
def projection(years: int, base_hours: float, rate: float) -> None:
    """Project Linear vs Compound CHRONOS-1 yield over a decade."""
    from rich.table import Table

    from cortex.engine.compound_yield import CompoundProjector

    try:
        report = CompoundProjector.project(
            base_hours_per_year=base_hours,
            reuse_rate=rate,
            years=years,
        )

        table = Table(title=f"CHRONOS-1 Ω₁₁ {years}-Year Projection (r={rate})")
        table.add_column("Year", justify="right", style="cyan")
        table.add_column("Linear (ΣH)", justify="right")
        table.add_column("Compound (∏H)", justify="right", style="bold yellow")
        table.add_column("Multiplier", justify="right", style="magenta")

        for yr in range(years):
            yr_lin = report.yearly_linear[yr]
            yr_comp = report.yearly_compound[yr]
            yr_mult = yr_comp / yr_lin if yr_lin > 0 else 0

            table.add_row(
                str(yr + 1),
                f"{yr_lin:,.0f}h",
                f"{yr_comp:,.0f}h",
                f"{yr_mult:.1f}x",
            )

        console.print(table)

        summary = (
            f"\n[cyan]Final Linear Yield:[/cyan] [white]{report.total_linear:,.0f}h[/white]\n"
            f"[magenta]Final Compound Yield:[/magenta] [bold yellow]{report.total_compound:,.0f}h[/bold yellow]\n"
            f"[green]Decade Multiplier:[/green] [bold white]{report.multiplier:,.1f}x[/bold white]\n\n"
            f"[dim]Axiom Ω₁₁ confirms exponential mastery.[/dim]"
        )
        console.print(
            Panel(summary, title="[bold magenta]10-Year Event Horizon[/bold magenta]", expand=False)
        )

    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e
