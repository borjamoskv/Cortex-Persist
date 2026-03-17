"""CORTEX CLI — Health dashboard command.

Rich terminal dashboard showing system health at a glance.
Added to the `cortex health` command group.
"""

from __future__ import annotations
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import console, get_db_path  # type: ignore[reportAttributeAccessIssue]


@click.command("dashboard")
@click.option("--db", "db_path", default=None, help="DB path override.")
def dashboard(db_path: Optional[str], samples: int, interval: float) -> None:
    """Rich interactive live dashboard for CORTEX Health."""
    from cortex.extensions.health.collector import HealthCollector
    from cortex.extensions.health.models import Grade
    from cortex.extensions.health.scorer import HealthScorer

    path = get_db_path(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    # ─── Grade Panel ──────────────────────────────────────
    grade_colors = {
        Grade.SOVEREIGN: "bright_green",
        Grade.EXCELLENT: "green",
        Grade.GOOD: "cyan",
        Grade.ACCEPTABLE: "yellow",
        Grade.DEGRADED: "red",
        Grade.FAILED: "bright_red",
    }
    color = grade_colors.get(hs.grade, "white")

    console.print()
    console.print(
        Panel(
            f"[bold {color}]{hs.grade.emoji} {hs.score:.1f}/100  Grade {hs.grade.letter}[/]",
            title="[bold]CORTEX HEALTH INDEX[/]",
            subtitle=f"[dim]{path}[/]",
            border_style=color,
            width=60,
        )
    )

    # ─── Metrics Table ────────────────────────────────────
    table = Table(
        title="Metric Breakdown",
        show_header=True,
        header_style="bold cyan",
        width=60,
    )
    table.add_column("Metric", style="bold")
    table.add_column("Bar", width=22)
    table.add_column("Value", justify="right")
    table.add_column("Weight", justify="right", style="dim")

    for m in metrics:
        filled = int(m.value * 20)
        bar = "█" * filled + "░" * (20 - filled)

        if m.value >= 0.8:
            val_color = "green"
        elif m.value >= 0.5:
            val_color = "yellow"
        else:
            val_color = "red"

        table.add_row(
            m.name.upper(),
            f"[{val_color}]{bar}[/]",
            f"[{val_color}]{m.value:.0%}[/]",
            f"{m.weight:.1f}",
        )

    console.print(table)

    # ─── Recommendations ──────────────────────────────────
    recs: list[str] = []
    warns: list[str] = []

    for m in metrics:
        if m.value < 0.5:
            warns.append(f"⚠️  {m.name}: critical ({m.value:.0%})")
        elif m.value < 0.8:
            recs.append(f"💡 {m.name}: could improve ({m.value:.0%})")

    if hs.score < 40:
        warns.append(f"⚠️  Overall: DEGRADED ({hs.grade.letter})")
    elif hs.score < 70:
        recs.append("💡 Run `cortex compact` to reduce entropy")

    if warns:
        console.print(
            Panel(
                "\n".join(warns),
                title="[bold red]Warnings[/]",
                border_style="red",
                width=60,
            )
        )

    if recs:
        console.print(
            Panel(
                "\n".join(recs),
                title="[bold yellow]Recommendations[/]",
                border_style="yellow",
                width=60,
            )
        )

    if not warns and not recs:
        console.print(
            Panel(
                "[green]✅ All systems nominal[/]",
                border_style="green",
                width=60,
            )
        )

    console.print()
