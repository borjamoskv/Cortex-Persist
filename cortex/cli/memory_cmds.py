"""CLI commands: store, search, recall, history."""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    _detect_agent_source,
    _run_async,
    _show_tip,
    cli,
    console,
    get_engine,
)
from cortex.cli.errors import err_empty_results
from cortex.cli.slow_tip import with_slow_tips


@cli.command()
@click.argument("project")
@click.argument("content")
@click.option(
    "--type",
    "fact_type",
    type=click.Choice(
        [
            "knowledge",
            "decision",
            "ghost",
            "preference",
            "identity",
            "issue",
            "error",
            "bridge",
            "world-model",
            "counterfactual",
        ]
    ),
    default="knowledge",
    help="Fact type",
)
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option(
    "--confidence",
    type=click.Choice(["C1", "C2", "C3", "C4", "C5", "stated", "inferred"]),
    default="stated",
    help="Confidence level",
)
@click.option("--source", default=None, help="Source of the fact")
@click.option("--ai-time", type=int, default=None, help="AI generation time")
@click.option(
    "--complexity",
    type=click.Choice(["low", "medium", "high", "god", "impossible"]),
    default=None,
    help="Task complexity",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store(project, content, fact_type, tags, confidence, source, ai_time, complexity, db) -> None:
    """Store a fact in CORTEX."""
    if not source:
        source = _detect_agent_source()

    engine = get_engine(db)
    try:
        meta = {}
        if ai_time is not None and complexity is not None:
            import dataclasses

            from cortex.timing.chronos import ChronosEngine

            metrics = ChronosEngine.analyze(ai_time, complexity)
            meta["chronos"] = dataclasses.asdict(metrics)
            console.print(
                f"[bold cyan]⏳ CHRONOS-1:[/] {metrics.asymmetry_factor:.1f}x asymmetry. {metrics.tip}"
            )

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        fact_id = _run_async(
            engine.store(
                project=project,
                content=content,
                fact_type=fact_type,
                tags=tag_list,
                confidence=confidence,
                source=source,
                meta=meta if meta else None,
            )
        )
        console.print(
            f"[[noir.cyber]✓[/]] Stored fact [[noir.gold]#{fact_id}[/]] in [[noir.yinmn]{project}[/]] [dim](source: {source})[/]"
        )
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--top", "-k", default=5, help="Number of results")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def search(query, project, top, db) -> None:
    """Semantic search across CORTEX memory."""
    engine = get_engine(db)
    try:
        with with_slow_tips("Buscando en CORTEX…", threshold=2.0, interval=8.0, engine=engine):
            with console.status("[noir.violet]Searching...[/]"):
                results = _run_async(engine.search(query, project=project, top_k=top))
        if not results:
            err_empty_results(
                "resultados de búsqueda",
                suggestion="Prueba con otros términos o sin filtro de proyecto.",
            )
            return
        table = Table(title=f"🔍 Results for: '{query}'")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="noir.yinmn", width=15)
        table.add_column("Content", width=50)
        table.add_column("Type", style="noir.violet", width=10)
        table.add_column("Score", style="noir.cyber", width=6)
        for r in results:
            content = r.content[:80] + "..." if len(r.content) > 80 else r.content
            table.add_row(str(r.fact_id), r.project, content, r.fact_type, f"{r.score:.2f}")
        console.print(table)
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db) -> None:
    """Load full context for a project."""
    engine = get_engine(db)
    try:
        with with_slow_tips(f"Cargando contexto de {project}…", threshold=2.0, engine=engine):
            facts = _run_async(engine.recall(project))
        if not facts:
            err_empty_results(
                f"facts para '{project}'",
                suggestion=f"Verifica el nombre del proyecto con: cortex list -p {project}",
            )
            return
        console.print(
            Panel(
                f"[bold]{project}[/] — {len(facts)} active facts",
                title="🧠 CORTEX Recall",
                border_style="cyan",
            )
        )
        by_type: dict[str, list] = {}
        for f in facts:
            by_type.setdefault(f.fact_type, []).append(f)
        for ftype, type_facts in by_type.items():
            console.print(f"\n[bold magenta]═══ {ftype.upper()} ({len(type_facts)}) ═══[/]")
            for f in type_facts:
                tags_str = f" [dim]{', '.join(f.tags)}[/]" if f.tags else ""
                console.print(f"  [dim]#{f.id}[/] {f.content}{tags_str}")
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
                f"[bold]{project}[/] — {len(facts)} facts ({label})",
                title="⏰ CORTEX History",
                border_style="yellow",
            )
        )
        for f in facts:
            status = "[green]●[/]" if f.is_active() else "[red]○[/]"
            console.print(f"  {status} [dim]#{f.id}[/] [{f.valid_from[:10]}] {f.content[:80]}")
    finally:
        _run_async(engine.close())
