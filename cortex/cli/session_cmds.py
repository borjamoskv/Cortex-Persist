"""CLI commands for session management and rejection logic."""

import subprocess
import sys
import time

import click
from rich.panel import Panel

from cortex.cli.common import DEFAULT_DB, cli, close_engine_sync, console, get_engine


def _get_uncommitted_changes() -> list[str]:
    """Return a list of uncommitted modified files via git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        changes = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                changes.append(line)
        return changes
    except Exception:
        return []


def _has_recent_decision(engine, minutes: int = 60) -> bool:
    """Check if there is a 'decision' fact created within the last N minutes."""
    try:
        conn = engine._get_sync_conn()
        # Fetch the most recent decision
        row = conn.execute(
            "SELECT created_at FROM facts WHERE fact_type = 'decision' ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not row:
            return False

        created_at_iso = row[0]

        # Parse ISO 8601 string to timestamp
        # The DB typically stores it as 'YYYY-MM-DDTHH:MM:SS.mmmmmm+00:00'
        # We can use fromisoformat
        from datetime import datetime

        dt = datetime.fromisoformat(created_at_iso)
        dt_timestamp = dt.timestamp()

        current_time = time.time()
        age_minutes = (current_time - dt_timestamp) / 60.0

        return age_minutes <= minutes
    except Exception as e:
        import logging

        logging.debug(f"Failed to fetch recent decision: {e}")
        return True  # Default to true to not block if there's an error


@cli.command("logout")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--force", is_flag=True, default=False, help="Bypass immune rejection")
def logout_cmd(db: str, force: bool) -> None:
    """End the current sovereign session, verifying entropic safety (Ω₆)."""
    engine = get_engine(db)
    try:
        if force:
            console.print(
                "[noir.gold]⚠️  FORZADO: Cierre de sesión (Bypass de inmunidad activo).[/]"
            )
            return

        # 1. Check for uncommitted entropy
        changes = _get_uncommitted_changes()

        if changes:
            # We have file changes, we must ensure there's a recent decision
            # Zenón's Razor: 60 minutes threshold for causal engram
            has_decision = _has_recent_decision(engine, minutes=60)

            if not has_decision:
                console.print(
                    Panel(
                        "🚨 Ω₆ — ZENÓN'S RAZOR: Cierre de sesión rechazado.\n\n"
                        "Se ha detectado una fluctuación en la entropía de los archivos que no "
                        "ha sido colapsada en un [noir.cyber]Engrama Causal "
                        "(Decision)[/noir.cyber] reciente.\n\n"
                        "[white]La intención sin registro es entropía pura. Por favor, "
                        "documente sus decisiones antes de partir o utilice el bypass "
                        "soberano:[/white]\n\n"
                        "[dim]cortex store --type decision ...[/dim]\n"
                        "[dim]cortex logout --force[/dim]",
                        title="[noir.cyber]EPISTEMIC FILTER[/noir.cyber]",
                        border_style="red",
                    )
                )

                console.print("\n[dim]Entropía detectada:[/dim]")
                for c in changes[:5]:
                    console.print(f"  [noir.yinmn]→ {c}[/noir.yinmn]")
                if len(changes) > 5:
                    console.print(f"  [dim]...y {len(changes) - 5} archivos adicionales.[/dim]")

                sys.exit(1)

        console.print(
            Panel(
                "[bold green]✓[/bold green] [noir.cyan]Sesión cerrada con integridad. "
                "No hay entropía huérfana detectada.[/noir.cyan]",
                title="[noir.cyber]ZENÓN-1 OK[/noir.cyber]",
                border_style="green",
            )
        )

        # Show Sovereign Tip
        from cortex.cli.common import _show_tip

        _show_tip(engine)

    finally:
        close_engine_sync(engine)
