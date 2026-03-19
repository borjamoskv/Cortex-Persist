"""
CORTEX v8 — Research Commands (I+D).

Proactive architectural innovation and exergy benchmarking.
"""

import click

from cortex.cli.common import console, get_engine
from cortex.research.frontier_id import FrontierRD


@click.group("research")
def research_cmds():
    """🚀 Sovereign Research: Architectural Innovation & Exergy."""
    pass

@research_cmds.command("frontier")
@click.option("--project", "-p", required=True, help="Target project for R&D cycle.")
@click.option("--model", "-m", help="Override default frontier model.")
@click.option("--timeout", "-t", default=180.0, type=float, help="Timeout in seconds.")
@click.option("--no-persist", is_flag=True, default=False, help="Skip DB persistence.")
def frontier_research_cmd(project: str, model: str | None, timeout: float, no_persist: bool):
    """Execute a high-fidelity R&D cycle via the Triad (NEMO, DAEDALUS, ICARUS)."""
    console.print(f"[noir.cyber]🐺 Awakening Frontier R&D Agent for: {project}...[/noir.cyber]")

    engine = get_engine()
    rd_engine = FrontierRD(
        engine=engine,
        model_override=model,
        timeout=timeout,
        persist=not no_persist
    )

    with console.status("[noir.yinmn]NEMO is scanning for ghosts...[/noir.yinmn]"):
        # Helper to run async in click
        from cortex.cli.common import _run_async
        result = _run_async(rd_engine.run_cycle(project))

    if result["status"] == "SUCCESS":
        duration = result['latency'] / 1000
        console.print(f"[bold green]✔ R&D Cycle executed successfully ({duration:.1f}s)[/]")
        console.print("\n[bold noir.gold]🧪 EXERGY REPORT:[/]")
        console.print(result["report"])

        # Hormonal feedback
        balance = result["endocrine_state"]
        msg = f"CORTISOL={balance['CORTISOL']} | NG={balance['NEURAL_GROWTH']}"
        console.print(f"\n[dim]Hormonal Balance: {msg}[/dim]")
    else:
        console.print(f"[bold red]❌ R&D Cycle failed: {result.get('error')}[/bold red]")

