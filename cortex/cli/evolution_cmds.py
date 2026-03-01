"""CORTEX CLI — Evolution commands.

`cortex evolution` — Cognitive Evolution Rate (CER) analysis.

    cortex evolution status      Show CER metric and health zone
    cortex evolution frictions   List decisions with high surprise scores
"""

from __future__ import annotations

import click
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    _run_async,
    _show_tip,
    close_engine_sync,
    console,
    get_engine,
)


@click.group("evolution")
def evolution_cmds() -> None:
    """🧬 Cognitive Evolution Rate — measure how fast CORTEX evolves."""


@evolution_cmds.command("status")
@click.option("--project", "-p", default=None, help="Scope to a single project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def status_cmd(project: str | None, db: str) -> None:
    """Show CER metric, health zone, and friction summary."""
    from cortex.evolution.cer import CERConfig, compute_cer

    engine = get_engine(db)
    try:
        _run_async(engine.init_db())
        config = CERConfig()
        result = _run_async(compute_cer(engine, config, project=project))

        # Header
        scope = f" [{project}]" if project else " [all projects]"
        console.print(
            f"\n[bold #CCFF00]🧬 Cognitive Evolution Rate{scope}[/bold #CCFF00]\n"
        )

        # CER gauge
        cer_pct = result.cer * 100
        bar_width = 40
        filled = int(cer_pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        console.print(
            f"  CER: [{result.health_color}]{cer_pct:.1f}%[/{result.health_color}]"
            f"  {result.health_icon} {result.health.upper()}"
        )
        console.print(f"  [{result.health_color}]{bar}[/{result.health_color}]")
        console.print()

        # Stats table
        table = Table(
            border_style="#2E5090",
            show_header=False,
            padding=(0, 2),
        )
        table.add_column("Metric", style="dim", width=22)
        table.add_column("Value", style="white")

        table.add_row("Total decisions", str(result.total_decisions))
        table.add_row("Frictions detected", f"[bold]{result.discrepancies}[/bold]")
        table.add_row("Centroid norm", f"{result.centroid_norm:.4f}")
        table.add_row(
            "Sweet spot",
            f"[dim]{config.sweet_spot_low*100:.0f}%–{config.sweet_spot_high*100:.0f}%[/dim]",
        )
        table.add_row(
            "Threshold",
            f"[dim]cosine < {config.surprise_threshold}[/dim]",
        )

        console.print(table)

        # Zone interpretation
        console.print()
        if result.health == "stagnant":
            console.print(
                "[cyan]🧊 Sistema estancado — Gc domina. "
                "Pocas ideas nuevas están entrando al sistema.[/cyan]"
            )
        elif result.health == "evolving":
            console.print(
                "[green]🌱 Evolución saludable — fricción productiva "
                "entre inteligencia fluida y cristalizada.[/green]"
            )
        else:
            console.print(
                "[red]🌋 Caótico — demasiada divergencia. "
                "Las decisiones no forman un modelo coherente.[/red]"
            )

        # Top 3 frictions preview
        if result.frictions:
            console.print(
                f"\n[dim]Top friction: {result.frictions[0].content[:80]}... "
                f"(surprise: {result.frictions[0].surprise_score:.3f})[/dim]"
            )

        _show_tip(engine)

    finally:
        close_engine_sync(engine)


@evolution_cmds.command("frictions")
@click.option("--project", "-p", default=None, help="Scope to a single project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--limit", "-n", default=20, help="Max frictions to show")
def frictions_cmd(project: str | None, db: str, limit: int) -> None:
    """List decisions with high surprise scores (evolutionary frictions)."""
    from cortex.evolution.cer import compute_cer

    engine = get_engine(db)
    try:
        _run_async(engine.init_db())
        result = _run_async(compute_cer(engine, project=project))

        if not result.frictions:
            console.print("[dim]No frictions detected — system is coherent.[/dim]")
            _show_tip(engine)
            return

        table = Table(
            title=f"🧬 Evolutionary Frictions — CER {result.cer*100:.1f}%",
            title_style="bold #CCFF00",
            border_style="#2E5090",
            show_lines=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Surprise", style="bold #CCFF00", width=9)
        table.add_column("Project", style="#D4AF37", width=16)
        table.add_column("Age", style="dim", width=6)
        table.add_column("Decision", style="white", max_width=70)

        for i, friction in enumerate(result.frictions[:limit], 1):
            # Color surprise score
            s = friction.surprise_score
            if s > 0.6:
                s_color = "bold red"
            elif s > 0.45:
                s_color = "bold yellow"
            else:
                s_color = "dim"

            age_str = (
                f"{friction.age_days:.0f}d"
                if friction.age_days >= 1
                else f"{friction.age_days * 24:.0f}h"
            )

            table.add_row(
                str(i),
                f"[{s_color}]{s:.3f}[/{s_color}]",
                friction.project,
                age_str,
                friction.content[:70],
            )

        console.print(table)
        console.print(
            f"\n[dim]{result.discrepancies} frictions / "
            f"{result.total_decisions} decisions | "
            f"{result.health_icon} {result.health}[/dim]"
        )

        _show_tip(engine)

    finally:
        close_engine_sync(engine)
