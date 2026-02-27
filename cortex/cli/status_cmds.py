"""CLI commands: status."""

from __future__ import annotations

import json
import sqlite3

import click
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, _run_async, cli, console, get_engine
from cortex.cli.errors import err_db_not_found, handle_cli_error


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output) -> None:
    """Show CORTEX health and statistics."""
    engine = get_engine(db)
    try:
        try:
            s = _run_async(engine.stats())
        except FileNotFoundError:
            err_db_not_found(db)
            return
        except sqlite3.OperationalError as e:
            handle_cli_error(e, db_path=db, context="consulta de estado")
            return

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
