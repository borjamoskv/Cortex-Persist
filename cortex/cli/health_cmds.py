"""CORTEX CLI — Health command group.

Commands for the CORTEX Health Index — monitoring and scoring.
Thin CLI wrapper; all logic lives in cortex.health.
"""

from __future__ import annotations

from typing import Optional

import click

from cortex.cli.common import console, get_db_path  # type: ignore[reportAttributeAccessIssue]


def render_sparkline(data: list[float]) -> str:
    """Generate a terminal sparkline from a list of floats."""
    ticks = " ▂▃▄▅▆▇█"
    if not data:
        return ""
    min_v, max_v = min(data), max(data)
    if max_v == min_v:
        return ticks[4] * len(data)
    step = (max_v - min_v) / (len(ticks) - 1)
    return "".join(ticks[int(round((v - min_v) / step))] for v in data)


@click.group("health")
def health_group() -> None:
    """CORTEX Health Index — system health monitoring."""


@health_group.command("check")
@click.option("--db", "db_path", default=None, help="DB path override.")
def check(db_path: Optional[str]) -> None:
    """Quick boolean health check (healthy/degraded)."""
    from cortex.extensions.health import HealthCollector, HealthScorer

    path = get_db_path(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    summary = HealthScorer.summarize(hs)

    console.print(f"\n{summary}\n")

    for m in hs.metrics:
        bar_len = int(m.value * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        console.print(f"  {m.name:12s} [{bar}] {m.value:.0%} (w={m.weight})")
    console.print()


@health_group.command("report")
@click.option("--db", "db_path", default=None)
@click.option("--json", "as_json", is_flag=True, default=False)
def report(db_path: Optional[str], as_json: bool) -> None:
    """Full health report with recommendations."""
    import asyncio
    import json

    from cortex.extensions.health import HealthMixin

    class _Engine(HealthMixin):
        _db_path = get_db_path(db_path)

    engine = _Engine()
    rep = asyncio.run(engine.health_report())

    if as_json:
        console.print(json.dumps(rep.to_dict(), indent=2))
        return

    hs = rep.score
    console.print(
        f"\n{hs.grade.emoji} CORTEX Health Report: "
        f"[bold]{hs.score:.1f}/100[/] "
        f"(Grade [cyan]{hs.grade.letter}[/])"
        f"  trend: {rep.trend}\n"
    )

    if rep.warnings:
        console.print("[bold red]Warnings:[/]")
        for w in rep.warnings:
            console.print(f"  ⚠️  {w}")

    if rep.recommendations:
        console.print("\n[bold yellow]Recommendations:[/]")
        for r in rep.recommendations:
            console.print(f"  💡 {r}")

    console.print(f"\n  DB: [dim]{rep.db_path}[/]\n")


@health_group.command("score")
@click.option("--db", "db_path", default=None)
def score(db_path: Optional[str]) -> None:
    """Print only the numeric health score (0-100)."""
    from cortex.extensions.health import HealthCollector, HealthScorer

    path = get_db_path(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    console.print(f"{hs.score:.1f}")


@health_group.command("trend")
@click.option("--db", "db_path", default=None)
@click.option("--samples", default=10, help="Number of samples to collect.")
@click.option("--interval", default=1.0, help="Seconds between samples.")
def trend(db_path: Optional[str], samples: int, interval: float) -> None:
    """Live health trend monitoring with sparklines."""
    import time

    from rich.progress import track

    from cortex.extensions.health import HealthCollector, HealthScorer
    from cortex.extensions.health.trend import TrendDetector

    path = get_db_path(db_path)
    collector = HealthCollector(db_path=path)
    detector = TrendDetector(window_size=samples)
    scores: list[float] = []

    console.print(f"\n[dim]Collecting {samples} health samples...[/]")
    for _ in track(range(samples), description="Sampling"):
        metrics = collector.collect_all()
        hs = HealthScorer.score(metrics)
        scores.append(hs.score)
        detector.push(hs.score)
        if _ < samples - 1:
            time.sleep(interval)

    spark = render_sparkline(scores)
    drift = detector.detect_drift()
    slope = detector.slope()

    color = "green" if drift == "improving" else ("red" if drift == "degrading" else "yellow")
    console.print(f"\n📈 Trend: [{color}]{drift}[/] (slope: {slope:+.3f})")
    console.print(f"Sparkline: [cyan]{spark}[/]\n")


# ─── Attach dashboard subcommand ─────────────────────────────
from cortex.cli.health_dashboard import dashboard  # noqa: E402

health_group.add_command(dashboard)
