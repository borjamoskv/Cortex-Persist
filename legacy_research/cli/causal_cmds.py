# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json

import click
from rich.panel import Panel
from rich.table import Table

from babylon60.cli.common import (
    DEFAULT_DB,
    _run_async,
    _show_tip,
    cli,
    console,
    get_engine,
)
from babylon60.cli.memory_cmds import memory_cmds


@memory_cmds.command("trace-episode")
@click.argument("query", required=False, default="")
@click.option("--fact-id", "-f", type=int, default=0, help="Trace from a specific fact ID")
@click.option("--project", "-p", default="", help="Scope to project")
@click.option("--limit", "-n", default=3, help="Max episodes to return")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def trace_episode(query, fact_id, project, limit, db) -> None:
    """Trace causal episodes - reconstruct WHY something happened.

    Two modes:
      By query:   cortex memory trace-episode "migration failed"
      By fact ID: cortex memory trace-episode --fact-id 42
    """
    if not query and fact_id == 0:
        console.print("[red]Provide a query or --fact-id[/]")
        return

    engine = get_engine(db)
    try:
        if fact_id > 0:
            with console.status("[noir.violet]Tracing causal chain...[/]"):
                episode = _run_async(engine.trace_episode(fact_id))
            console.print(
                Panel(
                    f"Root: #{episode.root_fact_id}  |  "
                    f"Depth: {episode.depth}  |  "
                    f"Nodes: {len(episode.fact_chain)}  |  "
                    f"Entropy: {episode.entropy_density:.2f}",
                    title=f"🧬 Causal Episode from fact #{fact_id}",
                    border_style="cyan",
                )
            )
            console.print(episode.summary)
        else:
            with console.status("[noir.violet]Searching causal episodes...[/]"):
                episodes = _run_async(engine.recall_episode(query, project, limit))
            if not episodes:
                from babylon60.cli.errors import err_empty_results

                err_empty_results(
                    "episodios causales",
                    suggestion="Prueba con otros términos.",
                )
                return
            for ep in episodes:
                console.print(
                    Panel(
                        f"Root: #{ep.root_fact_id}  |  "
                        f"Depth: {ep.depth}  |  "
                        f"Nodes: {len(ep.fact_chain)}  |  "
                        f"Entropy: {ep.entropy_density:.2f}",
                        title=f"🧬 Episode [{ep.project}]",
                        border_style="cyan",
                    )
                )
                console.print(ep.summary)
                console.print()
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@memory_cmds.command("trace-chain")
@click.argument("fact_id", type=int)
@click.option(
    "--direction",
    "-d",
    type=click.Choice(["up", "down"]),
    default="down",
    help="Traversal direction: up (toward root) or down (toward leaves)",
)
@click.option("--depth", default=10, help="Max recursion depth")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def trace_chain(fact_id, direction, depth, db) -> None:
    """Traverse the causal chain from a fact.

    Examples:
      cortex memory trace-chain 42            # All descendants
      cortex memory trace-chain 42 -d up      # Ancestry toward root
    """
    engine = get_engine(db)
    try:
        with console.status("[noir.violet]Tracing causal chain...[/]"):
            chain = _run_async(
                engine.get_causal_chain(
                    fact_id,
                    direction=direction,
                    max_depth=depth,
                )
            )

        if not chain:
            console.print(f"[dim]No causal chain found from fact #{fact_id}[/]")
            return

        arrow = "↑" if direction == "up" else "↓"
        table = Table(
            title=(f"🧬 Causal Chain {arrow} from #{fact_id} ({len(chain)} nodes)"),
        )
        table.add_column("Depth", style="dim", width=5)
        table.add_column("ID", style="bold", width=6)
        table.add_column("Type", style="noir.violet", width=10)
        table.add_column("Conf", style="noir.cyber", width=5)
        table.add_column("Taint", width=10)
        table.add_column("Content", width=40)
        table.add_column("Parent", style="dim", width=6)

        for f in chain:
            content = f.get("content", "")[:50]
            parent_id = f.get("parent_decision_id")
            parent_str = str(parent_id) if parent_id else "-"
            meta = f.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (ValueError, TypeError, json.JSONDecodeError):
                    meta = {}

            taint = meta.get("taint_status", "clean")
            taint_color = (
                "red" if taint == "tainted" else "yellow" if taint == "suspect" else "green"
            )

            table.add_row(
                str(f.get("causal_depth", "?")),
                str(f.get("id", "?")),
                f.get("fact_type", "?"),
                f.get("confidence", "C?"),
                f"[{taint_color}]{taint}[/]",
                content,
                parent_str,
            )

        console.print(table)
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db) -> None:
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
    try:
        facts = _run_async(engine.history(project, as_of=as_of))
        label = f"as of {as_of}" if as_of else "all time"
        console.print(
            Panel(
                f"[bold]{project}[/] - {len(facts)} facts ({label})",
                title="⏰ CORTEX History",
                border_style="yellow",
            )
        )
        for f in facts:
            if isinstance(f, dict):
                is_active = f.get("valid_until") is None
                fid = f.get("id", "?")
                valid_from = (f.get("valid_from") or "")[:10]
                content = (f.get("content") or "")[:80]
            else:
                is_active = f.is_active()
                fid = f.id
                valid_from = f.valid_from[:10]
                content = f.content[:80]
            badge = "[green]●[/]" if is_active else "[dim]○[/]"
            console.print(f"  {badge} [dim]#{fid}[/] [{valid_from}] {content}")
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--threshold", default=0.88, help="Cosine similarity threshold (0.0 to 1.0)")
@click.option("--simulate", is_flag=True, default=False, help="Do not save changes, just list them")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def dedupe(project: str, threshold: float, simulate: bool, db: str) -> None:
    """Run Memory Archaeology to deduplicate and crystallize facts."""
    from babylon60.memory.memory_archaeology import MemoryArchaeologist

    engine = get_engine(db)
    try:
        with console.status(f"[noir.violet]Running memory archaeology for {project}...[/]"):
            archaeologist = MemoryArchaeologist(engine)
            res = _run_async(archaeologist.run_archaeology(project, threshold, simulate))

        if simulate:
            console.print(
                f"[bold yellow]Simulation Complete:[/] "
                f"Would condense {res['condensed']} clusters "
                f"and tombstone {res['tombstoned']} facts."
            )
        else:
            console.print(
                f"[[noir.cyber]✓[/]] [bold green]Archaeology Complete:[/] "
                f"'{project}' optimized. Condensed {res['condensed']} "
                f"items, tombstoned {res['tombstoned']}."
            )
    finally:
        _run_async(engine.close())


cli.add_command(history)
cli.add_command(dedupe)
