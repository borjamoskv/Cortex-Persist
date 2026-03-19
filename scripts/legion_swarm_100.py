#!/usr/bin/env python3
"""LEGION-Ω 100-Agent Remediation Swarm — Standalone Entry Point.

Usage:
    python scripts/legion_swarm_100.py --db ~/.cortex/cortex.db --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.database.pool import CortexConnectionPool
from cortex.engine.async_engine import AsyncCortexEngine
from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine


async def main():
    parser = argparse.ArgumentParser(description="LEGION-Ω 100-Agent Remediation Swarm")
    parser.add_argument("--db", default="~/.cortex/cortex.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--report", help="Path to save JSON report")
    args = parser.parse_args()

    console = Console()

    db_path = str(Path(args.db).expanduser())
    if not Path(db_path).exists():
        console.print(f"[bold red]Error:[/bold red] Database not found at {db_path}")
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold cyan]LEGION-Ω[/bold cyan] [slate_blue]100-Agent Remediation Swarm[/slate_blue]\n"
            f"[dim]DB-Path: {db_path}[/dim]\n"
            f"[dim]Mode: {'DRY-RUN' if args.dry_run else 'PRODUCTION'}[/dim]",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_init = progress.add_task("Initializing 100-agent mesh...", total=100)

        pool = CortexConnectionPool(db_path, read_only=args.dry_run)
        await pool.initialize()
        progress.advance(task_init, 30)

        cortex_engine = AsyncCortexEngine(pool, db_path)
        await cortex_engine.initialize()
        progress.advance(task_init, 30)

        engine = LegionRemediationEngine(db_path, dry_run=args.dry_run, engine=cortex_engine)
        progress.advance(task_init, 40)

        task_rem = progress.add_task("Executing remediation cycle...", total=None)
        report = await engine.execute()
        progress.update(task_rem, completed=100, description="Remediation cycle complete.")

    # Summary Table
    table = Table(title="Swarm Remediation Summary", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")

    table.add_row("Facts Scanned", str(report.total_facts_scanned))
    table.add_row("Issues Identified", str(report.total_issues_found))
    table.add_row("Fixes Applied", f"[green]{report.fixes_applied}[/green]")
    table.add_row("Fixes Rejected", f"[yellow]{report.fixes_rejected}[/yellow]")
    table.add_row("Fixes Failed", f"[red]{report.fixes_failed}[/red]")

    console.print(table)

    if args.report:
        engine.save_report(report, args.report)
        console.print(f"[dim]Report saved to {args.report}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
