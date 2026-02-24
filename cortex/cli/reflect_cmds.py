"""CLI commands for CORTEX Reflection System — reflect + inject."""

from __future__ import annotations

import sqlite3

import click
from rich.panel import Panel

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.cli.errors import err_empty_results, handle_cli_error

__all__ = ["reflect", "inject"]


@cli.command()
@click.argument("project")
@click.argument("summary")
@click.option("--errors", default=None, help="Comma-separated errors encountered")
@click.option("--decisions", default=None, help="Comma-separated decisions made")
@click.option("--source", default="auto-reflect", help="Source tag")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def reflect(project, summary, errors, decisions, source, db) -> None:
    """Store a post-mortem reflection for the current session."""
    from cortex.thinking.reflection import generate_reflection

    engine = get_engine(db)
    try:
        error_list = [e.strip() for e in errors.split(",")] if errors else []
        decision_list = [d.strip() for d in decisions.split(",")] if decisions else []

        fact_id = generate_reflection(
            engine=engine,
            project=project,
            summary=summary,
            errors=error_list,
            decisions=decision_list,
            source=source,
        )
        console.print(f"[green]✓[/] Reflection [bold]#{fact_id}[/] stored in [cyan]{project}[/]")
        if error_list:
            console.print(f"  [red]✗[/] {len(error_list)} error(s) logged")
        if decision_list:
            console.print(f"  [blue]→[/] {len(decision_list)} decision(s) logged")
    except (sqlite3.Error, OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, db_path=db, context="storing reflection")
    finally:
        engine.close_sync()


@cli.command()
@click.argument("project", required=False, default=None)
@click.option("--hint", default="general session context", help="Context hint for semantic search")
@click.option("--top", "top_k", default=5, type=int, help="Number of reflections to retrieve")
@click.option(
    "--format",
    "fmt",
    default="markdown",
    type=click.Choice(["markdown", "json"]),
    help="Output format",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def inject(project, hint, top_k, fmt, db) -> None:
    """Retrieve relevant past learnings for system_prompt injection."""
    from cortex.thinking.reflection import (
        format_injection_json,
        format_injection_markdown,
        inject_reflections,
    )

    engine = get_engine(db)
    try:
        learnings = inject_reflections(
            engine=engine,
            context_hint=hint,
            project=project,
            top_k=top_k,
        )

        if fmt == "json":
            output = format_injection_json(learnings)
            console.print(output)
        else:
            output = format_injection_markdown(learnings)
            if learnings:
                console.print(
                    Panel(
                        output,
                        title="🧠 CORTEX Injection",
                        subtitle=f"{len(learnings)} learning(s) retrieved",
                        border_style="cyan",
                    )
                )
            else:
                err_empty_results("prior reflections")
    except (sqlite3.Error, OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, db_path=db, context="injecting reflections")
    finally:
        engine.close_sync()
