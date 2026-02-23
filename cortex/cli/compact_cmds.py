"""CLI commands: compact, compact-status."""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.compactor import (
    CompactionStrategy,
    compact,
    compact_session,
    get_compaction_stats,
)

_STRATEGY_MAP = {s.value: s for s in CompactionStrategy}


@cli.command()
@click.argument("project")
@click.option(
    "--strategy",
    "-s",
    multiple=True,
    type=click.Choice([s.value for s in CompactionStrategy]),
    help="Strategies to apply (default: all). Can be specified multiple times.",
)
@click.option("--dry-run", is_flag=True, help="Preview without executing.")
@click.option(
    "--threshold",
    "-t",
    default=0.85,
    type=float,
    help="Similarity threshold for dedup (0.0–1.0).",
)
@click.option("--max-age", default=90, type=int, help="Days threshold for staleness.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
@click.option("--db", default=DEFAULT_DB, help="Database path.")
def compact_cmd(project, strategy, dry_run, threshold, max_age, force, db) -> None:
    """Run auto-compaction on a project's facts.

    Deduplicates, consolidates errors, and prunes stale facts.
    Original facts are deprecated (never deleted) — full audit trail preserved.
    """
    engine = get_engine(db)
    try:
        # Parse strategies
        strategies = [_STRATEGY_MAP[s] for s in strategy] if strategy else None
        strategy_label = ", ".join(s for s in strategy) if strategy else "all"

        if dry_run:
            console.print(
                f"[dim]🔍 Dry-run compaction for[/] [bold cyan]{project}[/] "
                f"[dim](strategies: {strategy_label})[/]"
            )
        else:
            if not force:
                console.print(
                    f"[yellow]⚠ Compacting[/] [bold]{project}[/] "
                    f"[dim](strategies: {strategy_label})[/]"
                )
                if not click.confirm("Proceed?"):
                    console.print("[dim]Aborted.[/]")
                    return

        result = compact(
            engine,
            project=project,
            strategies=strategies,
            dry_run=dry_run,
            similarity_threshold=threshold,
            max_age_days=max_age,
        )

        # Display results
        if result.reduction == 0 and not result.details:
            console.print(
                f"[green]✓[/] No compaction needed for [bold]{project}[/]. "
                f"Memory is clean ({result.original_count} facts)."
            )
            return

        panel_lines = [
            f"[bold]Facts:[/] {result.original_count} → {result.compacted_count} "
            f"([green]-{result.reduction}[/])",
        ]
        if result.deprecated_ids:
            panel_lines.append(f"[bold]Deprecated:[/] {len(result.deprecated_ids)} fact(s)")
        if result.new_fact_ids:
            panel_lines.append(f"[bold]New consolidated:[/] {len(result.new_fact_ids)} fact(s)")
        for detail in result.details:
            panel_lines.append(f"  [dim]→ {detail}[/]")

        title = "🗜️ Compaction Result"
        if dry_run:
            title += " (DRY RUN)"

        console.print(
            Panel(
                "\n".join(panel_lines),
                title=title,
                border_style="cyan" if not dry_run else "yellow",
            )
        )

    finally:
        engine.close_sync()


@cli.command("compact-status")
@click.argument("project", required=False)
@click.option("--db", default=DEFAULT_DB, help="Database path.")
def compact_status(project, db) -> None:
    """Show compaction history and statistics."""
    engine = get_engine(db)
    try:
        stats = get_compaction_stats(engine, project)

        if stats["total_compactions"] == 0:
            console.print("[dim]No compaction history found.[/]")
            return

        console.print(
            f"\n[bold]Compaction Stats[/]"
            f"{f' — {project}' if project else ''}\n"
            f"  Total runs: [cyan]{stats['total_compactions']}[/]\n"
            f"  Total deprecated: [yellow]{stats['total_deprecated']}[/]\n"
        )

        if stats["history"]:
            table = Table(title="Recent Compactions", border_style="cyan")
            table.add_column("ID", style="bold", width=4)
            table.add_column("Project", style="cyan", width=16)
            table.add_column("Strategy", width=20)
            table.add_column("Before→After", width=14)
            table.add_column("Deprecated", width=10)
            table.add_column("When", style="dim", width=20)

            for entry in stats["history"]:
                table.add_row(
                    str(entry["id"]),
                    entry["project"],
                    entry["strategy"],
                    f"{entry['facts_before']}→{entry['facts_after']}",
                    str(entry["deprecated_count"]),
                    entry["timestamp"],
                )
            console.print(table)

    finally:
        engine.close_sync()


@cli.command("compact-session")
@click.argument("project")
@click.option("--max-facts", "-n", default=50, help="Max facts to include.")
@click.option("--db", default=DEFAULT_DB, help="Database path.")
def compact_session_cmd(project, max_facts, db) -> None:
    """Generate compressed context for LLM re-injection.

    Outputs a dense markdown summary of the most relevant active facts,
    grouped by type and sorted by importance. Ideal for pasting into
    a new conversation to avoid context rot.
    """
    engine = get_engine(db)
    try:
        output = compact_session(engine, project, max_facts=max_facts)
        console.print(output)
    finally:
        engine.close_sync()
