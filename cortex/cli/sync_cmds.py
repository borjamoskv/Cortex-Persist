"""CLI commands: sync, export, writeback."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click
from rich.panel import Panel

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.extensions.sync import export_obsidian, export_snapshot, export_to_json, sync_memory

__all__ = [
    "export",
    "obsidian",
    "sync",
    "writeback",
]


def _run_async(coro):
    """Helper to run async coroutines from sync CLI."""
    return asyncio.run(coro)


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(db) -> None:
    """Sincronizar ~/.agent/memory/ → CORTEX (incremental)."""
    engine = get_engine(db)

    async def _async_sync():
        try:
            await engine.init_db()
            with console.status("[bold blue]Sincronizando memoria...[/]"):
                # Fix: Wrap async call
                result = await sync_memory(engine)

            if result.had_changes:
                console.print(
                    Panel(
                        f"[bold green]✓ Sincronización completada[/]\n"
                        f"Facts: {result.facts_synced}\n"
                        f"Ghosts: {result.ghosts_synced}\n"
                        f"Errores: {result.errors_synced}\n"
                        f"Bridges: {result.bridges_synced}\n"
                        f"Omitidos (ya existían): {result.skipped}",
                        title="🔄 CORTEX Sync",
                        border_style="green",
                    )
                )
            else:
                console.print("[dim]Sin cambios desde la última sincronización.[/]")
            if result.errors:
                for err in result.errors:
                    console.print(f"[red]  ✗ {err}[/]")
        finally:
            # Fix: engine.close is async
            await engine.close()

    _run_async(_async_sync())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--out", help="Ruta de salida (por defecto depende del formato)")
@click.option(
    "--format",
    "fmt",
    default="snapshot",
    help="Formato: snapshot, notebooklm, json, csv, jsonl",
)
@click.option("--project", help="Filtrar por proyecto")
@click.option("--min-confidence", type=float, help="Confianza mínima (0.0-1.0)")
@click.option("--types", help="Tipos separados por coma (ej. rule,insight)")
def export(db, out, fmt, project, min_confidence, types) -> None:
    """Exportar datos o snapshot de CORTEX."""
    engine = get_engine(db)

    async def _async_export():
        nonlocal out
        try:
            await engine.init_db()
            fact_types = [t.strip() for t in types.split(",")] if types else None

            if fmt == "snapshot":
                out_path = Path(out or "~/.cortex/context-snapshot.md").expanduser()
                # Wrap async call
                await export_snapshot(
                    engine,
                    out_path,
                    project_filter=project,
                    min_confidence=min_confidence,
                    fact_types=fact_types,
                )
                console.print(f"[green]✓[/] Snapshot exportado a [cyan]{out_path}[/]")
            else:
                from cortex.utils.export import export_facts

                # Fetch facts through the new engine method
                facts = await engine.get_all_active_facts(project=project, fact_types=fact_types)

                # Filter by confidence if needed
                if min_confidence is not None:
                    # Simple numeric check if confidence is float-castable
                    def _check_conf(f_conf: Any) -> bool:
                        try:
                            return float(f_conf) >= min_confidence
                        except (ValueError, TypeError):
                            return True  # Keep non-numeric ones by default

                    facts = [f for f in facts if _check_conf(f.confidence)]

                output_str = export_facts(facts, fmt=fmt)

                # Default output filename
                if not out:
                    ext = "md" if fmt == "notebooklm" else fmt
                    out = f"cortex-export-{project or 'all'}.{ext}"

                out_path = Path(out).expanduser()
                out_path.write_text(output_str, encoding="utf-8")
                console.print(f"[green]✓[/] Datos ({fmt}) exportatorios a [cyan]{out_path}[/]")
        finally:
            # engine.close is async
            await engine.close()

    _run_async(_async_export())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def writeback(db) -> None:
    """Write-back: CORTEX DB → ~/.agent/memory/ (DB es Source of Truth)."""
    engine = get_engine(db)

    async def _async_writeback():
        try:
            await engine.init_db()
            result = await export_to_json(engine)
            if result.had_changes:
                console.print(
                    Panel(
                        f"[bold green]✓ Write-back completado[/]\n"
                        f"Archivos actualizados: {result.files_written}\n"
                        f"Archivos sin cambios: {result.files_skipped}\n"
                        f"Items exportados: {result.items_exported}",
                        title="🔄 CORTEX → JSON",
                        border_style="cyan",
                    )
                )
            else:
                console.print(
                    "[dim]Sin cambios en DB desde el último write-back. "
                    f"({result.files_skipped} archivos verificados)[/]"
                )
            for err in result.errors:
                console.print(
                    f"  [red]✗[/] {err}\n"
                    f"    [dim]Verifica permisos del directorio o ejecuta: cortex sync[/dim]"
                )
        finally:
            # Fix: engine.close is async
            await engine.close()

    _run_async(_async_writeback())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option(
    "--out",
    default="~/.cortex/obsidian-vault",
    help="Ruta del vault Obsidian de salida",
)
def obsidian(db, out) -> None:
    """Exportar CORTEX como vault de Obsidian con notas interconectadas."""
    engine = get_engine(db)

    async def _async_obsidian():
        try:
            await engine.init_db()
            out_path = Path(out).expanduser()
            with console.status("[bold blue]Generando vault Obsidian...[/]"):
                stats = await export_obsidian(engine, out_path)

            console.print(
                Panel(
                    f"[bold green]✓ Vault Obsidian generado[/]\n"
                    f"Notas creadas: {stats['notes_created']}\n"
                    f"Facts exportados: {stats['total_facts']}\n"
                    f"Proyectos: {', '.join(stats['projects'])}\n"
                    f"Tags: {len(stats['tags'])}\n"
                    f"Ruta: {stats['vault_path']}",
                    title="📓 CORTEX → Obsidian",
                    border_style="magenta",
                )
            )
        finally:
            await engine.close()

    _run_async(_async_obsidian())
