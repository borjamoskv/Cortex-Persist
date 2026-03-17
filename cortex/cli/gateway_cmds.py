"""CLI commands: gateway."""

from __future__ import annotations

import json

import click

from cortex.cli.common import DEFAULT_DB, console, get_engine


@click.group("gateway")
def gateway_cmds() -> None:
    """CORTEX gateway management commands."""


@gateway_cmds.command("health")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def health(db: str, as_json: bool) -> None:
    """Check gateway resonance and health."""
    # For now, it mirrors global health or specific gateway metrics if available
    from cortex.extensions.health import HealthCollector, HealthScorer

    engine = get_engine(db)
    collector = HealthCollector(db_path=db)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    if as_json:
        out = {
            "status": "healthy" if hs.score > 80 else "degraded",
            "score": hs.score,
            "grade": hs.grade.letter,
            "timestamp": hs.timestamp,
        }
        click.echo(json.dumps(out, indent=2))
        return

    console.print(
        f"\n[[noir.cyber]⚡[/]] Gateway Health: [bold]{hs.score:.1f}/100[/] ([noir.yinmn]{hs.grade.letter}[/])"
    )
    console.print(f"[dim]State: {'Resonant' if hs.score > 90 else 'Stable'}[/]\n")
    engine.close_sync()
