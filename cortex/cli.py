"""
CORTEX v4.0 — CLI Interface.

Command-line tool for the sovereign memory engine.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.engine import CortexEngine
from cortex.sync import export_snapshot, export_to_json, sync_memory
from cortex.timing import TimingTracker

console = Console()
DEFAULT_DB = "~/.cortex/cortex.db"


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance."""
    return CortexEngine(db_path=db)


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine."""
    return TimingTracker(engine._get_conn())


# ─── Main Group ──────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli():
    """CORTEX — The Sovereign Ledger for AI Agents."""
    pass


# ─── Init ────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def init(db):
    """Initialize CORTEX database."""
    engine = get_engine(db)
    engine.init_db()
    console.print(Panel(
        f"[bold green]✓ CORTEX v{__version__} initialized[/]\n"
        f"Database: {engine._db_path}",
        title="🧠 CORTEX",
        border_style="green",
    ))
    engine.close()


# ─── Store ───────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.argument("content")
@click.option("--type", "fact_type", default="knowledge", help="Fact type")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--confidence", default="stated", help="Confidence level")
@click.option("--source", default=None, help="Source of the fact")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store(project, content, fact_type, tags, confidence, source, db):
    """Store a fact in CORTEX."""
    engine = get_engine(db)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    fact_id = engine.store(
        project=project,
        content=content,
        fact_type=fact_type,
        tags=tag_list,
        confidence=confidence,
        source=source,
    )

    console.print(f"[green]✓[/] Stored fact [bold]#{fact_id}[/] in [cyan]{project}[/]")
    engine.close()


# ─── Search ──────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--top", "-k", default=5, help="Number of results")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def search(query, project, top, db):
    """Semantic search across CORTEX memory."""
    engine = get_engine(db)

    with console.status("[bold blue]Searching...[/]"):
        results = engine.search(query, project=project, top_k=top)

    if not results:
        console.print("[yellow]No results found.[/]")
        engine.close()
        return

    table = Table(title=f"🔍 Results for: '{query}'")
    table.add_column("#", style="dim", width=4)
    table.add_column("Project", style="cyan", width=15)
    table.add_column("Content", width=50)
    table.add_column("Type", style="magenta", width=10)
    table.add_column("Score", style="green", width=6)

    for r in results:
        content = r.content[:80] + "..." if len(r.content) > 80 else r.content
        table.add_row(
            str(r.fact_id),
            r.project,
            content,
            r.fact_type,
            f"{r.score:.2f}",
        )

    console.print(table)
    engine.close()


# ─── Recall ──────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db):
    """Load full context for a project."""
    engine = get_engine(db)
    facts = engine.recall(project)

    if not facts:
        console.print(f"[yellow]No facts found for project '{project}'[/]")
        engine.close()
        return

    console.print(Panel(
        f"[bold]{project}[/] — {len(facts)} active facts",
        title="🧠 CORTEX Recall",
        border_style="cyan",
    ))

    # Group by type
    by_type: dict[str, list] = {}
    for f in facts:
        by_type.setdefault(f.fact_type, []).append(f)

    for ftype, type_facts in by_type.items():
        console.print(f"\n[bold magenta]═══ {ftype.upper()} ({len(type_facts)}) ═══[/]")
        for f in type_facts:
            tags_str = f" [dim]{', '.join(f.tags)}[/]" if f.tags else ""
            console.print(f"  [dim]#{f.id}[/] {f.content}{tags_str}")

    engine.close()


# ─── History ─────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db):
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
    facts = engine.history(project, as_of=as_of)

    label = f"as of {as_of}" if as_of else "all time"
    console.print(Panel(
        f"[bold]{project}[/] — {len(facts)} facts ({label})",
        title="⏰ CORTEX History",
        border_style="yellow",
    ))

    for f in facts:
        status = "[green]●[/]" if f.is_active() else "[red]○[/]"
        console.print(
            f"  {status} [dim]#{f.id}[/] [{f.valid_from[:10]}] {f.content[:80]}"
        )

    engine.close()


# ─── Status ──────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output):
    """Show CORTEX health and statistics."""
    engine = get_engine(db)

    try:
        s = engine.stats()
    except (sqlite3.OperationalError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[dim]Run 'cortex init' first.[/]")
        engine.close()
        return

    if json_output:
        click.echo(json.dumps(s, indent=2))
        engine.close()
        return

    table = Table(title="🧠 CORTEX Status")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Version", __version__)
    table.add_row("Database", s["db_path"])
    table.add_row("Size", f"{s['db_size_mb']} MB")
    table.add_row("Total Facts", str(s["total_facts"]))
    table.add_row("Active Facts", f"[green]{s['active_facts']}[/]")
    table.add_row("Deprecated", f"[dim]{s['deprecated_facts']}[/]")
    table.add_row("Projects", str(s["project_count"]))
    table.add_row("Embeddings", str(s["embeddings"]))
    table.add_row("Transactions", str(s["transactions"]))

    if s["types"]:
        types_str = ", ".join(f"{t}: {c}" for t, c in s["types"].items())
        table.add_row("By Type", types_str)

    console.print(table)
    engine.close()


# ─── Migrate ─────────────────────────────────────────────────────

@cli.command()
@click.option("--source", default="~/.agent/memory", help="v3.1 memory directory")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate(source, db):
    """Import CORTEX v3.1 data into v4.0."""
    from cortex.migrate import migrate_v31_to_v40

    engine = get_engine(db)
    engine.init_db()

    with console.status("[bold blue]Migrating v3.1 → v4.0...[/]"):
        stats = migrate_v31_to_v40(engine, source)

    console.print(Panel(
        f"[bold green]✓ Migration complete![/]\n"
        f"Facts imported: {stats['facts_imported']}\n"
        f"Errors imported: {stats['errors_imported']}\n"
        f"Bridges imported: {stats['bridges_imported']}\n"
        f"Sessions imported: {stats['sessions_imported']}",
        title="🔄 v3.1 → v4.0 Migration",
        border_style="green",
    ))
    engine.close()


# ─── Sync ────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(db):
    """Sincronizar ~/.agent/memory/ → CORTEX (incremental)."""


    engine = get_engine(db)
    engine.init_db()

    with console.status("[bold blue]Sincronizando memoria...[/]"):
        result = sync_memory(engine)

    if result.had_changes:
        console.print(Panel(
            f"[bold green]✓ Sincronización completada[/]\n"
            f"Facts: {result.facts_synced}\n"
            f"Ghosts: {result.ghosts_synced}\n"
            f"Errores: {result.errors_synced}\n"
            f"Bridges: {result.bridges_synced}\n"
            f"Omitidos (ya existían): {result.skipped}",
            title="🔄 CORTEX Sync",
            border_style="green",
        ))
    else:
        console.print("[dim]Sin cambios desde la última sincronización.[/]")

    if result.errors:
        for err in result.errors:
            console.print(f"[red]  ✗ {err}[/]")

    engine.close()


# ─── Export ──────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--out", default="~/.cortex/context-snapshot.md", help="Ruta de salida")
def export(db, out):
    """Exportar snapshot de CORTEX a markdown (para lectura automática del agente)."""


    engine = get_engine(db)
    out_path = Path(out).expanduser()
    export_snapshot(engine, out_path)
    console.print(f"[green]✓[/] Snapshot exportado a [cyan]{out_path}[/]")
    engine.close()


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def writeback(db):
    """Write-back: CORTEX DB → ~/.agent/memory/ (DB es Source of Truth)."""


    engine = get_engine(db)
    result = export_to_json(engine)

    if result.had_changes:
        console.print(Panel(
            f"[bold green]✓ Write-back completado[/]\n"
            f"Archivos actualizados: {result.files_written}\n"
            f"Archivos sin cambios: {result.files_skipped}\n"
            f"Items exportados: {result.items_exported}",
            title="🔄 CORTEX → JSON",
            border_style="cyan",
        ))
    else:
        console.print(
            "[dim]Sin cambios en DB desde el último write-back. "
            f"({result.files_skipped} archivos verificados)[/]"
        )

    for err in result.errors:
        console.print(f"[red]  ✗ {err}[/]")

    engine.close()


# ─── Delete (Soft-Delete + Auto Write-back) ──────────────────────

@cli.command()
@click.argument("fact_id", type=int)
@click.option("--reason", "-r", default=None, help="Razón de la eliminación")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def delete(fact_id, reason, db):
    """Soft-delete: depreca un fact y auto-sincroniza JSON."""
    engine = get_engine(db)
    conn = engine._get_conn()

    # Mostrar qué se va a borrar
    row = conn.execute(
        "SELECT project, content, fact_type FROM facts WHERE id = ? AND valid_until IS NULL",
        (fact_id,),
    ).fetchone()

    if not row:
        console.print(f"[red]✗ No se encontró fact activo con ID {fact_id}[/]")
        engine.close()
        return

    console.print(
        f"[dim]Deprecando:[/] [bold]#{fact_id}[/] "
        f"[cyan]{row[0]}[/] ({row[2]}) — {row[1][:80]}..."
    )

    success = engine.deprecate(fact_id, reason or "deleted-via-cli")

    if success:
        # Auto write-back (Closed Loop)

        wb = export_to_json(engine)
        console.print(
            f"[green]✓[/] Fact #{fact_id} deprecado. "
            f"Write-back: {wb.files_written} archivos actualizados."
        )
    else:
        console.print(f"[red]✗ No se pudo deprecar fact #{fact_id}[/]")

    engine.close()


# ─── List (Read) ─────────────────────────────────────────────────

@cli.command("list")
@click.option("--project", "-p", default=None, help="Filtrar por proyecto")
@click.option("--type", "fact_type", default=None, help="Filtrar por tipo")
@click.option("--limit", "-n", default=20, help="Máximo de resultados")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def list_facts(project, fact_type, limit, db):
    """Listar facts activos (tabulado)."""
    engine = get_engine(db)
    conn = engine._get_conn()

    query = "SELECT id, project, content, fact_type, tags, confidence FROM facts WHERE valid_until IS NULL"
    params = []

    if project:
        query += " AND project = ?"
        params.append(project)
    if fact_type:
        query += " AND fact_type = ?"
        params.append(fact_type)

    query += " ORDER BY project, fact_type, id"
    query += f" LIMIT {limit}"

    rows = conn.execute(query, params).fetchall()

    if not rows:
        console.print("[dim]No se encontraron facts activos.[/]")
        engine.close()
        return

    table = Table(title=f"CORTEX Facts ({len(rows)})", border_style="cyan")
    table.add_column("ID", style="bold", width=5)
    table.add_column("Proyecto", style="cyan", width=18)
    table.add_column("Tipo", width=10)
    table.add_column("Contenido", width=60)
    table.add_column("Tags", style="dim", width=15)

    for row in rows:
        content_preview = row[2][:57] + "..." if len(row[2]) > 60 else row[2]
        tags = json.loads(row[4]) if row[4] else []
        tags_str = ", ".join(tags[:2]) + ("…" if len(tags) > 2 else "")
        table.add_row(str(row[0]), row[1], row[3], content_preview, tags_str)

    console.print(table)
    engine.close()


# ─── Edit (Deprecate + Store + Auto Write-back) ─────────────────

@cli.command()
@click.argument("fact_id", type=int)
@click.argument("new_content")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def edit(fact_id, new_content, db):
    """Editar un fact: depreca el viejo y crea uno nuevo con el contenido actualizado."""
    engine = get_engine(db)
    conn = engine._get_conn()

    # Obtener fact original
    row = conn.execute(
        "SELECT project, content, fact_type, tags, confidence, source FROM facts "
        "WHERE id = ? AND valid_until IS NULL",
        (fact_id,),
    ).fetchone()

    if not row:
        console.print(f"[red]✗ No se encontró fact activo con ID {fact_id}[/]")
        engine.close()
        return

    project, old_content, fact_type, tags_json, confidence, source = row
    tags = json.loads(tags_json) if tags_json else None

    # Deprecar el viejo
    engine.deprecate(fact_id, f"edited → new version")

    # Crear el nuevo con los mismos metadatos
    new_id = engine.store(
        project=project,
        content=new_content,
        fact_type=fact_type,
        tags=tags,
        confidence=confidence,
        source=source or "edit-via-cli",
    )

    # Auto write-back

    wb = export_to_json(engine)

    console.print(
        f"[green]✓[/] Fact #{fact_id} → #{new_id} editado.\n"
        f"  [dim]Antes:[/] {old_content[:60]}...\n"
        f"  [bold]Ahora:[/] {new_content[:60]}...\n"
        f"  Write-back: {wb.files_written} archivos actualizados."
    )
    engine.close()


# ─── Time Tracking ───────────────────────────────────────────────

@cli.command("time")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--days", "-d", default=1, help="Number of days (default: 1 = today)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def time_cmd(project, days, db):
    """Show time tracking summary."""
    engine = get_engine(db)
    engine.init_db()
    t = get_tracker(engine)

    if days <= 1:
        summary = t.today(project=project)
        title = "⏱ Today's Time"
    else:
        summary = t.report(project=project, days=days)
        title = f"⏱ Last {days} Days"

    if summary.total_seconds == 0:
        console.print("[yellow]No time tracked yet.[/]")
        engine.close()
        return

    table = Table(title=title)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total", summary.format_duration(summary.total_seconds))
    table.add_row("Entries", str(summary.entries))
    table.add_row("Heartbeats", str(summary.heartbeats))

    if summary.by_category:
        for cat, secs in sorted(summary.by_category.items(), key=lambda x: -x[1]):
            table.add_row(f"  {cat}", summary.format_duration(secs))

    if summary.by_project:
        table.add_row("", "")
        for proj, secs in sorted(summary.by_project.items(), key=lambda x: -x[1]):
            table.add_row(f"  📁 {proj}", summary.format_duration(secs))

    if summary.top_entities:
        table.add_row("", "")
        for entity, count in summary.top_entities[:5]:
            table.add_row(f"  📄 {entity}", f"{count} hits")

    console.print(table)
    engine.close()


@cli.command("heartbeat")
@click.argument("project")
@click.argument("entity", default="")
@click.option("--category", "-c", default=None, help="Activity category")
@click.option("--branch", "-b", default=None, help="Git branch")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def heartbeat_cmd(project, entity, category, branch, db):
    """Record an activity heartbeat."""
    engine = get_engine(db)
    engine.init_db()
    t = get_tracker(engine)

    hb_id = t.heartbeat(
        project=project,
        entity=entity,
        category=category,
        branch=branch,
    )
    t.flush()

    console.print(f"[green]✓[/] Heartbeat [bold]#{hb_id}[/] → [cyan]{project}[/]/{entity}")
    engine.close()


if __name__ == "__main__":
    cli()
