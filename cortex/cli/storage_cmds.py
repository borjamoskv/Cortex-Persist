"""
CORTEX v6.0 — Storage CLI Commands.

Commands for managing CORTEX storage backends:
  storage-init-pg   Initialize PostgreSQL schema (idempotent)
  storage-status    Show current storage backend and health
"""

from __future__ import annotations

import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import _run_async, cli, console


@cli.command("storage-init-pg")
@click.option(
    "--dsn",
    default=None,
    envvar="POSTGRES_DSN",
    help="PostgreSQL DSN (default: $POSTGRES_DSN)",
    show_envvar=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate connection without applying schema.",
)
@click.option(
    "--skip-extensions",
    is_flag=True,
    default=False,
    help="Skip pgvector/pg_trgm extension creation (for restricted users).",
)
def storage_init_pg(dsn: str | None, dry_run: bool, skip_extensions: bool) -> None:
    """Initialize CORTEX PostgreSQL schema.

    Applies all table definitions, indexes, and extensions to the target
    PostgreSQL database. Safe to run multiple times (idempotent).

    \b
    Required:
      POSTGRES_DSN=postgresql://user:pass@host:5432/cortex

    \b
    Example:
      POSTGRES_DSN=postgresql://... cortex storage-init-pg
      cortex storage-init-pg --dsn postgresql://... --dry-run
    """
    if not dsn:
        console.print(
            "[bold red]✗ POSTGRES_DSN not set.[/]\n"
            "[dim]Provide via --dsn or $POSTGRES_DSN env var.[/]"
        )
        raise click.Abort()

    async def _run() -> None:
        from cortex.storage.postgres import PostgresBackend

        with console.status("[bold #CCFF00]Connecting to PostgreSQL...[/]"):
            backend = PostgresBackend(
                dsn=dsn,
                min_size=1,
                max_size=5,
                auto_init_schema=False,  # Manual control here
            )
            await backend.connect()

        # Health check
        healthy = await backend.health_check()
        if not healthy:
            console.print("[bold red]✗ Health check failed. Cannot proceed.[/]")
            await backend.close()
            return

        console.print("[bold #CCFF00]✓ PostgreSQL connection healthy.[/]")

        if dry_run:
            console.print("[dim]--dry-run: Schema NOT applied.[/]")
            await backend.close()
            return

        # Skip extensions if requested
        if skip_extensions:
            from cortex.storage.pg_schema import PG_ALL_SCHEMA

            with console.status(
                f"[bold blue]Applying {len(PG_ALL_SCHEMA)} schema statements (no extensions)...[/]"
            ):
                for schema_sql in PG_ALL_SCHEMA:
                    await backend.executescript(schema_sql)
        else:
            with console.status("[bold blue]Applying full schema + extensions...[/]"):
                await backend.initialize_schema()

        # Verify core table
        rows = await backend.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'facts'"
        )
        table_ok = len(rows) == 1

        await backend.close()

        # Report
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold")
        grid.add_column()
        grid.add_row("Backend", "PostgreSQL")
        grid.add_row("DSN", _sanitize_dsn(dsn))
        schema_status = (
            "[bold #CCFF00]\u2713 Applied[/]"
            if table_ok
            else "[bold red]\u2717 Verification failed[/]"
        )
        grid.add_row("Schema", schema_status)
        grid.add_row("Mode", "skip-extensions" if skip_extensions else "full")

        console.print(
            Panel(
                grid,
                title="[bold #0A0A0A on #D4AF37]  CORTEX — PostgreSQL Init [/]",
                border_style="#CCFF00",
            )
        )

    _run_async(_run())


@cli.command("storage-status")
def storage_status() -> None:
    """Show current storage backend mode and health."""

    async def _run() -> None:
        from cortex.storage import get_storage_mode

        mode = get_storage_mode()

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold #D4AF37")
        grid.add_column()

        grid.add_row("Mode", f"[bold #CCFF00]{mode.value.upper()}[/]")
        grid.add_row(
            "Env CORTEX_STORAGE",
            os.environ.get("CORTEX_STORAGE", "[dim]not set \u2192 local[/]"),
        )

        if mode.value == "postgres":
            dsn = os.environ.get("POSTGRES_DSN", "")
            grid.add_row("POSTGRES_DSN", _sanitize_dsn(dsn) if dsn else "[red]NOT SET[/]")

            if dsn:
                await _check_pg_health(dsn, grid)

        elif mode.value == "turso":
            url = os.environ.get("TURSO_DATABASE_URL", "[dim]not set[/]")
            grid.add_row("TURSO_DATABASE_URL", url)

        else:  # local
            from cortex.core.config import DB_PATH

            grid.add_row("DB Path", str(DB_PATH))
            grid.add_row("Exists", "[#CCFF00]✓[/]" if DB_PATH.exists() else "[red]✗[/]")

        console.print(
            Panel(
                grid,
                title="[bold #0A0A0A on #D4AF37]  CORTEX Storage [/]",
                border_style="#2E5090",
            )
        )

    _run_async(_run())


def _sanitize_dsn(dsn: str) -> str:
    """Hide password from DSN for display."""
    if "@" in dsn and ":" in dsn:
        try:
            pre_at = dsn.split("@")[0]
            post_at = dsn.split("@")[1]
            if ":" in pre_at:
                user_part = pre_at.rsplit(":", 1)[0]
                return f"{user_part}:***@{post_at}"
        except (IndexError, ValueError):
            pass
    return dsn


async def _check_pg_health(dsn: str, grid: Table) -> None:
    """Probe PostgreSQL connectivity and add health row to grid."""
    from cortex.storage.postgres import PostgresBackend

    try:
        backend = PostgresBackend(
            dsn=dsn,
            min_size=1,
            max_size=2,
            auto_init_schema=False,
        )
        await backend.connect()
        healthy = await backend.health_check()
        await backend.close()
        status = (
            "[bold #CCFF00]\u2713 Connected[/]" if healthy else "[bold red]\u2717 Unreachable[/]"
        )
        grid.add_row("Health", status)
    except Exception as exc:
        grid.add_row("Health", f"[bold red]\u2717 Error: {exc}[/]")
