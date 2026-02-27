"""CLI commands for Sovereign Swarm operations."""

import asyncio
from pathlib import Path

import click
from rich.panel import Panel

from cortex.cli.common import cli, console


@cli.group()
def swarm():
    """SOVEREIGN SWARM — Orchestration of specialized agents (130/100)."""
    pass


@swarm.command("audit")
@click.argument("path", type=click.Path(exists=True))
@click.option("--level", "-l", type=int, default=1, help="Escalation level (1-3)")
def swarm_audit(path, level):
    """Deep semantic audit of a file or directory using the swarm."""
    from cortex.mejoralo.swarm import MejoraloSwarm

    p = Path(path)
    files = [p] if p.is_file() else list(p.glob("**/*.py"))

    if not files:
        console.print("[yellow]No python files found.[/]")
        return

    swarm_engine = MejoraloSwarm(level=level)

    console.print(
        Panel(
            f"🐝 [bold]Sovereign Swarm Audit[/]\n"
            f"Path: [cyan]{path}[/]\n"
            f"Level: [bold red]{level}[/]\n"
            f"Specialists: [dim]ArchitectPrime, CodeNinja, SecurityWarden...[/]",
            border_style="magenta",
        )
    )

    with console.status("[bold magenta]Swarm is thinking...[/]"):
        findings = asyncio.run(swarm_engine.audit_files(files))

    if not findings:
        console.print("[green]✅ No critical issues found by the swarm.[/]")
    else:
        console.print(f"\n[bold red]Swarm Findings ({len(findings)}):[/]")
        for f in findings:
            console.print(f"  [red]•[/] {f}")


@swarm.command("refactor")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--level", "-l", type=int, default=1, help="Escalation level (1-3)")
@click.option("--issue", "-i", multiple=True, help="Specific issue to fix")
@click.option("--dry-run", is_flag=True, help="Show refactored code without overwriting")
def swarm_refactor(file, level, issue, dry_run):
    """Refactor a specific file using the full specialist squad."""
    from cortex.mejoralo.swarm import MejoraloSwarm

    p = Path(file)
    swarm_engine = MejoraloSwarm(level=level)

    issues = list(issue) or ["General optimization and quality improvement (130/100)"]

    console.print(
        Panel(
            f"🐝 [bold]Sovereign Swarm Refactor[/]\n"
            f"File: [cyan]{file}[/]\n"
            f"Level: [bold red]{level}[/]\n"
            f"Goal: [dim]{issues[0]}[/]",
            border_style="magenta",
        )
    )

    with console.status("[bold magenta]Swarm is synthesizing insights...[/]"):
        new_code = asyncio.run(swarm_engine.refactor_file(p, issues))

    if not new_code:
        console.print("[bold red]❌ Swarm failed to refactor the file.[/]")
        return

    if dry_run:
        from rich.syntax import Syntax

        syntax = Syntax(new_code, "python", theme="monokai", line_numbers=True)
        console.print("\n[bold green]--- Refactored Code (Preview) ---[/]")
        console.print(syntax)
    else:
        p.write_text(new_code)
        console.print(f"[bold green]✅ {file} refactored by the swarm.[/]")
