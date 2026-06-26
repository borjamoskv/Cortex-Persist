# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Coroutine
from typing import Any, TypeVar, cast

import click
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.cli.errors import err_empty_results, err_fact_not_found
from cortex_extensions.sync import export_to_json

__all__ = ["delete", "edit", "list_facts"]

_T = TypeVar("_T")


def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    return asyncio.run(coro)


@cli.command()
@click.argument("fact_id", type=int)
@click.option("--reason", "-r", default=None, help="Razón de la eliminación")
@click.option("--tenant-id", default="default", show_default=True, help="Tenant scope")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def delete(fact_id, reason, tenant_id, db) -> None:
    """Soft-delete: depreca un fact y auto-sincroniza JSON."""

    async def _do_delete():
        engine = get_engine(db)
        try:
            try:
                fact = await engine.get_fact(fact_id, tenant_id=tenant_id)
            except (KeyError, ValueError, sqlite3.Error):
                err_fact_not_found(fact_id)
                return
            if fact is None:
                err_fact_not_found(fact_id)
                return

            from cortex.engine.uncategorized.models import Fact

            fact = cast(Fact, fact)

            console.print(
                f"[dim]Deprecando:[/] [bold]#{fact_id}[/] "
                f"[cyan]{fact.project}[/] ({fact.fact_type}) - {fact.content[:80]}..."
            )
            success = await engine.deprecate(
                fact_id, reason or "deleted-via-cli", tenant_id=tenant_id
            )
            if success:
                wb = await export_to_json(engine)
                console.print(
                    f"[green]✓[/] Fact #{fact_id} deprecated (deprecado). "
                    f"Write-back: {wb.files_written} archivos actualizados."
                )
            else:
                console.print(f"[red]✗ No se pudo deprecar/deprecate fact #{fact_id}[/]")
        finally:
            await engine.close()

    _run_async(_do_delete())


@cli.command("list")
@click.option("--project", "-p", default=None, help="Filtrar por proyecto")
@click.option("--type", "fact_type", default=None, help="Filtrar por tipo")
@click.option("--limit", "-n", default=20, help="Máximo de resultados")
@click.option("--tenant-id", default="default", show_default=True, help="Tenant scope")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def list_facts(project, fact_type, limit, tenant_id, db) -> None:
    """Listar facts activos (tabulado)."""

    async def _do_list():
        engine = get_engine(db)
        try:
            async with engine.session() as conn:
                query = """
                    SELECT id, project, content, fact_type, tags, created_at
                    FROM facts WHERE valid_until IS NULL AND tenant_id = ?
                """
                params = [tenant_id]
                if project:
                    query += " AND project = ?"
                    params.append(project)
                if fact_type:
                    query += " AND fact_type = ?"
                    params.append(fact_type)
                query += " ORDER BY project, fact_type, id"
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                cursor = await conn.execute(query, params)
                rows = list(await cursor.fetchall())

            if not rows:
                filter_hint = ""
                if project:
                    filter_hint += f" proyecto='{project}'"
                if fact_type:
                    filter_hint += f" tipo='{fact_type}'"
                err_empty_results(
                    f"facts activos{filter_hint}",
                    suggestion="Prueba sin filtros: cortex list",
                )
                return
            table = Table(title=f"CORTEX Facts ({tenant_id}) ({len(rows)})", border_style="cyan")
            table.add_column("ID", style="bold", width=5)
            table.add_column("Proyecto", style="cyan", width=18)
            table.add_column("Tipo", width=10)
            table.add_column("Contenido", width=60)
            table.add_column("Tags", style="dim", width=15)

            from cortex.crypto import get_default_encrypter

            enc = get_default_encrypter()
            from cryptography.exceptions import InvalidTag

            for row in rows:
                raw_content = row[2]
                try:
                    content = enc.decrypt_str(raw_content, tenant_id=tenant_id)
                except (ValueError, TypeError, OSError, InvalidTag):
                    content = raw_content
                content_str = str(content) if content else ""
                content_preview = content_str[:57] + "..." if len(content_str) > 60 else content_str
                tags = json.loads(row[4]) if row[4] else []
                tags_str = ", ".join(tags[:2]) + ("…" if len(tags) > 2 else "")
                table.add_row(str(row[0]), row[1], row[3], content_preview, tags_str)
            console.print(table)
        finally:
            await engine.close()

    _run_async(_do_list())


@cli.command()
@click.argument("fact_id", type=int)
@click.argument("new_content")
@click.option("--tenant-id", default="default", show_default=True, help="Tenant scope")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def edit(fact_id, new_content, tenant_id, db) -> None:
    """Editar un fact: depreca el viejo y crea uno nuevo con el contenido actualizado."""

    async def _do_edit():
        engine = get_engine(db)
        try:
            try:
                fact = await engine.get_fact(fact_id, tenant_id=tenant_id)
            except (KeyError, ValueError, sqlite3.Error):
                err_fact_not_found(fact_id)
                return
            if fact is None:
                err_fact_not_found(fact_id)
                return

            from cortex.engine.uncategorized.models import Fact

            fact = cast(Fact, fact)

            await engine.deprecate(fact_id, "edited → new version", tenant_id=tenant_id)
            new_id = await engine.store(
                project=fact.project,
                content=new_content,
                tenant_id=tenant_id,
                fact_type=fact.fact_type,
                tags=fact.tags,
                confidence=fact.confidence,
                source=fact.source or "edit-via-cli",
            )
            wb = await export_to_json(engine)
            console.print(
                f"[green]✓[/] Fact #{fact_id} → #{new_id} editado.\n"
                f"  [dim]Antes:[/] {fact.content[:60]}...\n"
                f"  [bold]Ahora:[/] {new_content[:60]}...\n"
                f"  Write-back: {wb.files_written} archivos actualizados."
            )
        finally:
            await engine.close()

    _run_async(_do_edit())


@cli.command()
@click.argument("fact_id", type=int)
@click.option("--tenant-id", default="default", show_default=True, help="Tenant scope")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def inspect(fact_id, tenant_id, db) -> None:
    """Deep inspection of a fact (Double-Plane V2 facets)."""

    async def _do_inspect():
        engine = get_engine(db)
        try:
            from rich.panel import Panel
            from rich.table import Table

            # Content decryption handled by engine.retrieve
            fact = await engine.get_fact(fact_id, tenant_id=tenant_id)
            if not fact:
                err_fact_not_found(fact_id)
                return

            # Load tags and status from engine
            async with engine.session() as conn:
                cursor = await conn.execute(
                    "SELECT tag FROM fact_tags WHERE fact_id = ?", (str(fact_id),)
                )
                tags = [r[0] for r in await cursor.fetchall()]

                # Load status from enrichment_jobs
                cursor = await conn.execute(
                    "SELECT status, error_message FROM enrichment_jobs "
                    "WHERE fact_id = ? AND job_type = 'embedding'",
                    (str(fact_id),),
                )
                job = await cursor.fetchone()
                status = job[0] if job else "COMPLETED"  # Assume completed if no job pending
                error = job[1] if job else None

            info = Table.grid(padding=(0, 1))
            info.add_column(style="bold cyan", justify="right")
            info.add_column()

            info.add_row("ID:", f"#{fact.id}")
            info.add_row("Project:", fact.project)
            info.add_row("Type:", fact.fact_type)
            info.add_row("Tenant:", fact.tenant_id)
            info.add_row("Source:", fact.source or "unknown")
            info.add_row("Confidence:", fact.confidence)

            # Double-Plane Facets
            info.add_row("", "")
            info.add_row("[bold underline]Thermodynamic Plane[/]", "")
            info.add_row("Quadrant:", fact.quadrant)
            info.add_row("Tier:", fact.storage_tier)
            info.add_row("Exergy:", f"{fact.exergy_score:.2f}")

            info.add_row("", "")
            info.add_row("[bold underline]Semantic Plane[/]", "")
            info.add_row("Category:", fact.category)
            info.add_row("Yield:", f"{fact.yield_score:.2f}")
            info.add_row("Tags:", ", ".join(tags) if tags else "-")

            # Enrichment Process
            info.add_row("", "")
            info.add_row("[bold underline]Process status (P0 Decoupling)[/]", "")
            job_color = (
                "red" if status == "failed" else ("yellow" if status == "pending" else "green")
            )
            info.add_row("Enrichment:", f"[{job_color}]{status.upper()}[/]")
            if error:
                info.add_row("Error:", f"[red]{error}[/]")

            if fact.parent_id:
                info.add_row("", "")
                info.add_row("[bold underline]Causal Lineage[/]", "")
                info.add_row("Parent:", f"#{fact.parent_id}")
                if fact.relation_type:
                    info.add_row("Relation:", fact.relation_type)

            console.print(
                Panel(
                    info,
                    title=f"Fact [bold]#{fact_id}[/]",
                    expand=False,
                    border_style="bright_blue",
                )
            )

            console.print("\n[bold]Content:[/]")
            console.print(fact.content)

        finally:
            await engine.close()

    _run_async(_do_inspect())
