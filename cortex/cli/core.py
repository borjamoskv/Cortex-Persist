"""CLI commands: init, store, search, recall, history, status, migrate."""

from __future__ import annotations

import json
import sqlite3

import click
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.cli.errors import err_db_not_found, err_empty_results, handle_cli_error
from cortex.event_loop import sovereign_run


def _show_tip(engine=None) -> None:
    """Show a random contextual tip after CLI operations."""
    try:
        from cortex.tips import TipsEngine

        tips_engine = TipsEngine(engine, include_dynamic=engine is not None, lang="es")
        tip = tips_engine.random()
        console.print()
        console.print(
            Panel(
                f"[white]{tip.content}[/white]",
                title=f"[bold cyan]💡 {tip.category.value.upper()}[/bold cyan]",
                subtitle=f"[dim]{tip.source}[/dim]",
                border_style="bright_green",
                padding=(0, 2),
            )
        )
    except (ImportError, RuntimeError, OSError, ValueError):
        pass  # Tips are non-critical; never break the CLI


def _get_tip_text(engine=None) -> str:
    """Get a short tip string for inline display (spinners, status bars)."""
    try:
        from cortex.tips import TipsEngine

        tips_engine = TipsEngine(engine, include_dynamic=False, lang="es")
        tip = tips_engine.random()
        return f"[dim bright_green]💡 {tip.content}[/]"
    except (ImportError, RuntimeError, OSError, ValueError):
        return ""


__all__ = [
    "history",
    "init",
    "migrate",
    "migrate_graph",
    "recall",
    "search",
    "status",
    "store",
]


def _run_async(coro):
    """Helper to run async coroutines from sync CLI (sovereign uvloop)."""
    return sovereign_run(coro)


def _detect_agent_source() -> str:
    """Auto-detect the AI agent calling CORTEX from environment.

    Priority order:
    1. CORTEX_SOURCE env var (explicit override)
    2. Known IDE/agent environment markers
    3. Fallback to 'cli'
    """
    import os

    # Explicit override takes priority
    explicit = os.environ.get("CORTEX_SOURCE")
    if explicit:
        return explicit

    # Detect by known environment markers
    markers = [
        ("GEMINI_AGENT", "agent:gemini"),
        ("CURSOR_SESSION_ID", "agent:cursor"),
        ("CLAUDE_CODE_AGENT", "agent:claude-code"),
        ("WINDSURF_SESSION", "agent:windsurf"),
        ("COPILOT_AGENT", "agent:copilot"),
        ("KIMI_SESSION_ID", "agent:kimi"),
    ]
    for env_var, source_name in markers:
        if os.environ.get(env_var):
            return source_name

    # Check terminal program as fallback hint
    term = os.environ.get("TERM_PROGRAM", "")
    if "cursor" in term.lower():
        return "agent:cursor"
    if "vscode" in term.lower():
        return "ide:vscode"

    return "cli"


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def init(db) -> None:
    """Initialize CORTEX database."""
    engine = get_engine(db)
    try:
        engine.init_db_sync()
        console.print(
            Panel(
                f"[bold green]✓ CORTEX v{__version__} initialized[/]\nDatabase: {engine._db_path}",
                title="🧠 CORTEX",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.argument("content")
@click.option("--type", "fact_type", default="knowledge", help="Fact type")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--confidence", default="stated", help="Confidence level")
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
    # Auto-detect source from environment when not provided
    if not source:
        source = _detect_agent_source()

    engine = get_engine(db)
    try:
        meta = {}
        if ai_time is not None and complexity is not None:
            import dataclasses

            from cortex.chronos import ChronosEngine

            metrics = ChronosEngine.analyze(ai_time, complexity)
            meta["chronos"] = dataclasses.asdict(metrics)
            console.print(
                f"[bold cyan]⏳ CHRONOS-1:[/] {metrics.asymmetry_factor:.1f}x asymmetry. {metrics.tip}"
            )

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        fact_id = engine.store_sync(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=tag_list,
            confidence=confidence,
            source=source,
            meta=meta if meta else None,
        )
        console.print(
            f"[green]✓[/] Stored fact [bold]#{fact_id}[/] in [cyan]{project}[/] [dim](source: {source})[/]"
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
        tip_text = _get_tip_text(engine)
        spinner_msg = (
            f"[bold blue]Searching...[/]  {tip_text}" if tip_text else "[bold blue]Searching...[/]"
        )
        with console.status(spinner_msg):
            results = engine.search_sync(query, project=project, top_k=top)
        if not results:
            err_empty_results(
                "resultados de búsqueda",
                suggestion="Prueba con otros términos o sin filtro de proyecto.",
            )
            return
        table = Table(title=f"🔍 Results for: '{query}'")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="cyan", width=15)
        table.add_column("Content", width=50)
        table.add_column("Type", style="magenta", width=10)
        table.add_column("Score", style="green", width=6)
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
        facts = engine.recall_sync(project)
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
        facts = engine.history_sync(project, as_of=as_of)
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


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output) -> None:
    """Show CORTEX health and statistics."""
    engine = get_engine(db)
    try:
        try:
            s = engine.stats_sync()
        except FileNotFoundError:
            err_db_not_found(db)
            return
        except sqlite3.OperationalError as e:
            handle_cli_error(e, db_path=db, context="consulta de estado")
        if json_output:
            click.echo(json.dumps(s, indent=2))
            return
        table = Table(
            title="[bold #CCFF00]⚡ ESTADO SOBERANO (CORTEX v6)[/]", border_style="#6600FF"
        )
        table.add_column("Métrica", style="bold #D4AF37")
        table.add_column("Valor", style="cyan")
        table.add_row("Engine State", "[bold #06d6a0]Hiperconducción 130/100[/]")
        table.add_row("Entropía", "[dim]Aniquilada[/]")
        table.add_row("Database", s["db_path"])
        table.add_row("Size", f"{s['db_size_mb']} MB")
        table.add_row("Total Facts", str(s["total_facts"]))
        table.add_row("Active Facts", f"[bold #06d6a0]{s['active_facts']}[/]")
        table.add_row("Deprecated", f"[dim]{s['deprecated_facts']}[/]")
        table.add_row("Projects", str(s["project_count"]))
        table.add_row("Embeddings", str(s["embeddings"]))
        table.add_row("Transactions", str(s["transactions"]))
        if s["types"]:
            types_str = ", ".join(f"{t}: {c}" for t, c in s["types"].items())
            table.add_row("By Type", f"[dim]{types_str}[/]")
        console.print(table)
    finally:
        _run_async(engine.close())


@cli.command()
@click.option("--source", default="~/.agent/memory", help="v3.1 memory directory")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate(source, db) -> None:
    """Import CORTEX v3.1 data into v4.0."""
    from cortex.migrate import migrate_v31_to_v40

    engine = get_engine(db)
    engine.init_db()
    try:
        with console.status("[bold blue]Migrating v3.1 → v4.0...[/]"):
            stats = migrate_v31_to_v40(engine, source)
        console.print(
            Panel(
                f"[bold green]✓ Migration complete![/]\n"
                f"Facts imported: {stats['facts_imported']}\n"
                f"Errors imported: {stats['errors_imported']}\n"
                f"Bridges imported: {stats['bridges_imported']}\n"
                f"Sessions imported: {stats['sessions_imported']}",
                title="🔄 v3.1 → v4.0 Migration",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())


@cli.command("migrate-graph")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate_graph(db) -> None:
    """Migrate local SQLite graph data to Neo4j global knowledge graph."""
    engine = get_engine(db)
    try:
        from cortex.graph import GRAPH_BACKEND, process_fact_graph

        if GRAPH_BACKEND != "neo4j":
            console.print("[yellow]WARNING: CORTEX_GRAPH_BACKEND is not set to 'neo4j'.[/]")
            console.print(
                "[dim]Migration will only re-process data into SQLite unless you set CORTEX_GRAPH_BACKEND=neo4j.[/]"
            )
            if not click.confirm("Do you want to continue?", default=False):
                return
        conn = engine._get_conn()
        facts = conn.execute("SELECT id, content, project, created_at FROM facts").fetchall()
        console.print(f"[bold blue]Migrating {len(facts)} facts to Graph Memory...[/]")
        processed = 0
        with console.status("[bold blue]Processing...[/]") as prog_status:
            for fid, content, project, ts in facts:
                try:
                    process_fact_graph(conn, fid, content, project, ts)
                    processed += 1
                    if processed % 10 == 0:
                        prog_status.update(f"[bold blue]Processed {processed}/{len(facts)}...[/]")
                except (sqlite3.Error, OSError, RuntimeError) as e:
                    console.print(
                        f"[red]✗[/] Fact [bold]#{fid}[/] falló: [dim]{e}[/dim] "
                        f"— continúa con los siguientes."
                    )
        console.print(
            Panel(
                f"[bold green]✓ Graph Migration Complete![/]\n"
                f"Facts processed: {processed}\nBackend: {GRAPH_BACKEND}",
                title="🧠 Graph Migration",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())
