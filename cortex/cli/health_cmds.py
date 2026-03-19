"""CORTEX CLI — Health command group.

Commands for the CORTEX Health Index — monitoring and scoring.
Thin CLI wrapper; all logic lives in cortex.extensions.health.
"""

from __future__ import annotations

import click

from cortex.cli.common import DEFAULT_DB, console  # type: ignore[reportAttributeAccessIssue]
from cortex.cli.health_dashboard import dashboard


def _resolve_db(db_path: str | None) -> str:
    """Resolve DB path from arg or default."""
    return db_path or str(DEFAULT_DB)


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
def check(db_path: str | None) -> None:
    """Quick boolean health check (healthy/degraded)."""
    from cortex.extensions.health import HealthCollector, HealthScorer

    path = _resolve_db(db_path)
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
def report(db_path: str | None, as_json: bool) -> None:
    """Full health report with recommendations."""
    import asyncio
    import json

    from cortex.extensions.health import HealthMixin

    class _Engine(HealthMixin):
        _db_path = _resolve_db(db_path)

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

    # Sub-indices
    if hs.sub_indices:
        console.print("\n[bold]Sub-Indices:[/]")
        for idx_name, val in hs.sub_indices.items():
            filled = int(val / 100 * 20)
            bar = "█" * filled + "░" * (20 - filled)
            if val >= 80:
                color = "green"
            elif val >= 50:
                color = "yellow"
            else:
                color = "red"
            console.print(f"  {idx_name:16s} [{color}]{bar}[/] {val:.1f}/100")

    # Remediation actions for degraded metrics
    degraded = [m for m in hs.metrics if m.value < 0.5]
    if degraded:
        console.print("\n[bold]🔧 Actions:[/]")
        for m in degraded:
            rem = getattr(m, "remediation", "") or ""
            if rem:
                console.print(f"  🔧 {m.name}: {rem}")

    console.print(f"\n  DB: [dim]{rep.db_path}[/]\n")


@health_group.command("score")
@click.option("--db", "db_path", default=None)
def score(db_path: str | None) -> None:
    """Print only the numeric health score (0-100)."""
    from cortex.extensions.health import HealthCollector, HealthScorer

    path = _resolve_db(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    console.print(f"{hs.score:.1f}")


@health_group.command("trend")
@click.option("--db", "db_path", default=None)
@click.option("--live", is_flag=True, default=False, help="Live sampling mode.")
@click.option("--samples", default=10, help="Samples for live mode.")
@click.option("--interval", default=1.0, help="Seconds between live samples.")
def trend(db_path: str | None, live: bool, samples: int, interval: float) -> None:
    """Health trend from DB history (instant) or live sampling."""
    from cortex.extensions.health.trend import TrendDetector

    path = _resolve_db(db_path)

    if live:
        # Live sampling mode
        import time

        from rich.progress import track

        from cortex.extensions.health import HealthCollector, HealthScorer

        collector = HealthCollector(db_path=path)
        detector = TrendDetector(window_size=samples)
        scores: list[float] = []

        console.print(f"\n[dim]Collecting {samples} health samples...[/]")
        for i in track(range(samples), description="Sampling"):
            metrics = collector.collect_all()
            hs = HealthScorer.score(metrics)
            scores.append(hs.score)
            detector.push(hs.score)
            if i < samples - 1:
                time.sleep(interval)
    else:
        # DB history mode (instant)
        detector = TrendDetector(window_size=20)
        detector.load_from_db(path, limit=20)
        scores = list(detector._scores)

        if not scores:
            console.print(
                "\n[yellow]No health history found. Run `cortex health report` first.[/]\n"
            )
            return

    spark = render_sparkline(scores)
    drift = detector.detect_drift()
    slope = detector.slope()

    color = "green" if drift == "improving" else ("red" if drift == "degrading" else "yellow")
    console.print(f"\n📈 Trend: [{color}]{drift}[/] (slope: {slope:+.3f})")
    console.print(f"  Samples: {len(scores)}")
    console.print(f"  Sparkline: [cyan]{spark}[/]\n")


@health_group.command("history")
@click.option("--db", "db_path", default=None)
@click.option("--limit", default=20, help="Number of records to show.")
def history(db_path: str | None, limit: int) -> None:
    """Show persisted health score history."""
    from rich.table import Table

    from cortex.extensions.health.trend import TrendDetector

    path = _resolve_db(db_path)
    records = TrendDetector.query_history(path, limit=limit)

    if not records:
        console.print("\n[yellow]No health history found.[/]\n")
        return

    table = Table(
        title=f"Health History (last {limit})", show_header=True, header_style="bold cyan"
    )
    table.add_column("Timestamp", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")

    for rec in records:
        score_val = float(rec.get("score", 0))
        grade = str(rec.get("grade", ""))
        ts = str(rec.get("timestamp", ""))[:19]
        if score_val >= 85:
            color = "green"
        elif score_val >= 70:
            color = "cyan"
        elif score_val >= 55:
            color = "yellow"
        else:
            color = "red"
        table.add_row(ts, f"[{color}]{score_val:.1f}[/]", grade)

    console.print()
    console.print(table)
    console.print()


@health_group.command("fix")
@click.option("--db", "db_path", default=None)
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be fixed.")
def fix(db_path: str | None, dry_run: bool) -> None:
    """Auto-remediation for degraded metrics."""
    from cortex.extensions.health import HealthCollector, HealthScorer
    from cortex.extensions.health.fix_registry import FixRegistry

    path = _resolve_db(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    registry = FixRegistry()
    degraded = [m.name for m in hs.metrics if m.value < 0.5]
    fixes = registry.applicable_fixes(degraded)

    if not fixes:
        console.print("\n[green]✅ No degraded metrics with available fixes.[/]\n")
        return

    for fa in fixes:
        risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(fa.risk, "white")
        if dry_run:
            console.print(
                f"  [dim]DRY-RUN[/] 🔧 {fa.metric}: {fa.label} [{risk_color}](risk: {fa.risk})[/]"
            )
        else:
            console.print(f"  🔧 {fa.metric}: {fa.label}...", end=" ")
            result = fa.fn(path)
            console.print(f"[green]{result}[/]")

    if dry_run:
        console.print("\n[dim]Use --no-dry-run to execute fixes.[/]\n")
    console.print()


@health_group.command("export")
@click.option("--db", "db_path", default=None)
@click.option("--format", "fmt", type=click.Choice(["prometheus", "json"]), default="prometheus")
def export(db_path: str | None, fmt: str) -> None:
    """Export health metrics (prometheus or json format)."""
    import json as json_mod

    from cortex.extensions.health import HealthCollector, HealthScorer
    from cortex.extensions.health.prometheus import export_prometheus

    path = _resolve_db(db_path)
    collector = HealthCollector(db_path=path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    if fmt == "prometheus":
        console.print(export_prometheus(hs))
    else:
        console.print(json_mod.dumps(hs.to_dict(), indent=2))


# ─── Attach dashboard subcommand ─────────────────────────────
health_group.add_command(dashboard)


@health_group.command("verify")
def verify():
    """Run structural invariant checks on the health system."""
    import sys

    from cortex.extensions.health.invariants import verify_health_system

    console.print("[bold blue]Running Health System Structural Invariants...[/bold blue]")
    try:
        verify_health_system()
        console.print("[bold green]✓ All structural invariants passed.[/bold green]")
    except AssertionError as e:
        console.print(f"[bold red]✗ Invariant violation: {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error running invariants: {e}[/bold red]")
        sys.exit(1)
