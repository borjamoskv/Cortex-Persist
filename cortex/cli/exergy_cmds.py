# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""
Exergy Engine CLI Commands.

CLI interface for the Exergy Daemon background loop.
"""

import asyncio

import click
from rich.panel import Panel

from cortex.cli.common import cli, console
from cortex.observability.exergy_engine import ExergyEngine

__all__ = [
    "exergy_cmds",
]


@cli.group(name="exergy", help="⚡ Exergy - autonomous self-healing and code/health sentinel.")
def exergy_cmds() -> None:
    """El motor de salud y auto-reparación de CORTEX."""


@exergy_cmds.command("daemon")
@click.option("--interval", default=21600, type=int, help="Check interval in seconds (default: 6h)")
def run_exergy_daemon(interval: int) -> None:
    """Run the Exergy Daemon self-healing background loop."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cortex-core"))
    from exergy_daemon import ExergyDaemon  # pyright: ignore[reportMissingImports]

    console.print(
        Panel(
            f"[bold #2B3BE5]⚡ EXERGY DAEMON ACTIVATED[/bold #2B3BE5]\n"
            f"Frecuencia de chequeo: [italic]{interval} segundos ({interval / 3600:.1f} horas)[/italic]\n"
            f"Modo: C5-REAL Soberano",
            border_style="#2B3BE5",
        )
    )

    daemon = ExergyDaemon(check_interval=interval)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
        console.print("[yellow]Exergy Daemon stopped.[/yellow]")


@exergy_cmds.command("entropy")
@click.argument("workflow")
def check_entropy(workflow: str) -> None:
    """Nivel 2: Comprueba la degradación entrópica (Entropy Drift) de un workflow."""
    engine = ExergyEngine()
    drift = engine.get_entropy_drift(workflow)
    status = drift.get("status", "UNKNOWN")

    color = "green" if status == "NOMINAL" else "red"
    console.print(f"[{color}]Workflow {workflow}: {status}[/{color}]")
    console.print(f"Expected Exergy: {drift.get('expected_exergy')}")
    console.print(f"Actual Exergy: {drift.get('actual_exergy')}")
    console.print(f"Deviation: {drift.get('deviation_pct')}%")


@exergy_cmds.command("predict")
@click.argument("workflow")
def predict_exergy(workflow: str) -> None:
    """Nivel 3: Predice el tiempo y exergía esperada de un workflow."""
    engine = ExergyEngine()
    pred = engine.predict(workflow)  # type: ignore

    console.print(f"[bold #2B3BE5]Predicción para: {workflow}[/bold #2B3BE5]")
    console.print(f"  Expected Runtime: {pred['predicted_runtime']}m")
    console.print(f"  Expected Exergy:  {pred['predicted_exergy']}")


@exergy_cmds.command("schedule")
@click.argument("workflows", nargs=-1)
def schedule_workflows(workflows: tuple) -> None:
    """Nivel 4: Lyapunov Scheduler. Ordena workflows por densidad de exergía."""
    if not workflows:
        console.print(
            "[red]Especifica workflows a priorizar (ej: cortex exergy schedule ship detective)[/red]"
        )
        return

    engine = ExergyEngine()
    ranked = engine.lyapunov_scheduler(list(workflows))

    console.print("[bold #2B3BE5]Lyapunov Scheduler Ranking[/bold #2B3BE5]")
    for r in ranked:
        console.print(
            f" [green]{r['workflow']}[/green] -> Priority {r['priority_score']} (Exergy: {r['expected_exergy']}, Runtime: {r['expected_runtime']}m)"
        )


@exergy_cmds.command("genomes")
def check_genomes() -> None:
    """Nivel 5: Imprime el rendimiento exergético por gen (herramienta/paradigma)."""
    engine = ExergyEngine()
    genes = engine.genome_analysis()

    console.print("[bold #2B3BE5]Workflow Genome Analysis[/bold #2B3BE5]")
    for g, stats in list(genes.items())[:10]:
        console.print(
            f" - [cyan]{g}[/cyan]: Avg Exergy {stats['average_exergy']} ({stats['occurrences']} ejecuciones)"
        )


@exergy_cmds.command("evolve")
@click.option("--window", default=1000, type=int, help="Historical window size for evolution.")
def evolve_scheduler(window: int) -> None:
    """Nivel 7: Meta-Lyapunov. Evoluciona el α_risk basado en errores contra-factuales."""
    engine = ExergyEngine()
    res = engine.evolve(window_size=window)

    console.print("[bold #2B3BE5]Meta-Lyapunov Update[/bold #2B3BE5]")
    console.print(f" - alpha_risk: {res['old_alpha']:.4f} → {res['new_alpha']:.4f}")
    console.print(f" - counterfactual_loss: {res['counterfactual_loss']:.4f} exergy units")
    console.print(f" - misses_evaluated: {res['miss_count']} historical errors")

    shift = ((res["new_alpha"] - res["old_alpha"]) / max(0.001, res["old_alpha"])) * 100
    color = "red" if shift > 0 else "green"
    console.print(f" - stability shift: [{color}]{shift:+.1f}%[/{color}]")


@exergy_cmds.command("aefm")
@click.option("--horizon", default=5, type=int, help="CAF trajectory horizon.")
@click.option(
    "--epsilon-path", default=0.1, type=float, help="Path noise to prevent bias collapse."
)
@click.option("--max-cycles", default=5, type=int, help="Max loops to run (for testing).")
def run_aefm(horizon: int, epsilon_path: float, max_cycles: int) -> None:
    """Starts the continuous Active Field reality deformation loop (Autonomous Exergy Field Mode)."""
    console.print("[bold #2B3BE5]🌌 Starting AEFM Daemon...[/bold #2B3BE5]")
    engine = ExergyEngine()

    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    engine.autonomous_field_daemon(
        horizon=horizon, epsilon_path=epsilon_path, recompute_fdf_min=10, max_cycles=max_cycles
    )
