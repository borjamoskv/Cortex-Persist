"""
CORTEX v5.0 — MOSKV-1 Daemon CLI.

Command-line interface for the persistent watchdog.

Commands:
    moskv-daemon start       Run daemon in foreground
    moskv-daemon check       Run once and exit
    moskv-daemon status      Show last check results
    moskv-daemon version     Show daemon version
    moskv-daemon install     Install macOS launchd agent
    moskv-daemon uninstall   Remove macOS launchd agent
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.extensions.daemon import (
    BUNDLE_ID,
    DEFAULT_COOLDOWN,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    MoskvDaemon,
)
from cortex.extensions.platform.sys import get_service_dir, is_linux, is_macos, is_windows

__all__ = [
    "PLIST_SOURCE",
    "check",
    "cli",
    "install",
    "main",
    "setup_logging",
    "start",
    "status",
    "uninstall",
    "version",
]

console = Console()

PLIST_SOURCE = Path(__file__).parent.parent / "launchd" / f"{BUNDLE_ID}.plist"


def _get_plist_dest() -> Path:
    """macOS launchd plist destination."""
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _get_systemd_unit() -> Path:
    """Linux systemd user unit destination."""
    svc_dir = get_service_dir()
    assert svc_dir is not None  # noqa: S101
    return svc_dir / f"{BUNDLE_ID}.service"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    )


# ─── Click Group ────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.option("--sites", default=None, help="Comma-separated URLs to monitor")
@click.option(
    "--stale-hours",
    type=float,
    default=DEFAULT_STALE_HOURS,
    help=f"Hours before a ghost project is stale (default: {DEFAULT_STALE_HOURS})",
)
@click.option(
    "--memory-stale-hours",
    type=float,
    default=DEFAULT_MEMORY_STALE_HOURS,
    help=f"Hours before CORTEX memory is stale (default: {DEFAULT_MEMORY_STALE_HOURS})",
)
@click.option(
    "--interval",
    type=int,
    default=DEFAULT_INTERVAL,
    help=f"Check interval in seconds (default: {DEFAULT_INTERVAL})",
)
@click.option(
    "--cooldown",
    type=float,
    default=DEFAULT_COOLDOWN,
    help=f"Seconds between duplicate alerts (default: {DEFAULT_COOLDOWN})",
)
@click.option("--no-notify", is_flag=True, help="Disable native notifications")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    sites: str | None,
    stale_hours: float,
    memory_stale_hours: float,
    interval: int,
    cooldown: float,
    no_notify: bool,
) -> None:
    """MOSKV-1 Persistent Watchdog Daemon."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["sites"] = sites.split(",") if sites else None
    ctx.obj["stale_hours"] = stale_hours
    ctx.obj["memory_stale_hours"] = memory_stale_hours
    ctx.obj["interval"] = interval
    ctx.obj["cooldown"] = cooldown
    ctx.obj["no_notify"] = no_notify

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _build_daemon(ctx: click.Context) -> MoskvDaemon:
    """Construct MoskvDaemon from Click context."""
    return MoskvDaemon(
        sites=ctx.obj["sites"],
        stale_hours=ctx.obj["stale_hours"],
        memory_stale_hours=ctx.obj["memory_stale_hours"],
        cooldown=ctx.obj["cooldown"],
        notify=not ctx.obj["no_notify"],
    )


# ─── Commands ─────────────────────────────────────────────────────────


@cli.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """Run daemon in foreground."""
    daemon = _build_daemon(ctx)
    daemon.run(interval=ctx.obj["interval"])


@cli.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Run all checks once and print results."""
    daemon = _build_daemon(ctx)
    status = daemon.check()

    # Header
    console.print()
    console.print(
        Panel(
            "[bold]MOSKV-1 DAEMON — CHECK[/]",
            border_style="cyan",
        )
    )

    # Sites
    site_table = Table(title="▸ Sites", show_header=True, header_style="bold")
    site_table.add_column("Status", width=4)
    site_table.add_column("URL", style="cyan")
    site_table.add_column("Latency")

    for site in status.sites:
        icon = "🟢" if site.healthy else "🔴"
        ms = f"{site.response_ms:.0f}ms" if site.healthy else f"[red]{site.error}[/]"
        site_table.add_row(icon, site.url, ms)

    if status.sites:
        console.print(site_table)
    else:
        console.print("  [dim]No sites configured. Use --sites or daemon_config.json[/]")
    console.print()

    # Ghosts
    console.print("[bold]▸ Stale Projects[/]")
    if status.stale_ghosts:
        for g in status.stale_ghosts:
            console.print(f"  💤 [yellow]{g.project}[/] — {g.hours_stale:.0f}h sin actividad")
    else:
        console.print("  [green]✅ All projects active[/]")
    console.print()

    # Memory
    console.print("[bold]▸ CORTEX Memory[/]")
    if status.memory_alerts:
        for m in status.memory_alerts:
            console.print(f"  ⚠️  [yellow]{m.file}[/] — {m.hours_stale:.0f}h stale")
    else:
        console.print("  [green]✅ Memory fresh[/]")
    console.print()

    # Duration
    console.print(f"  [dim]Check completed in {status.check_duration_ms:.0f}ms[/]")
    console.print()

    # Summary
    if status.all_healthy:
        console.print(Panel("[bold green]✅ ALL SYSTEMS NOMINAL[/]", border_style="green"))
    else:
        issues = len(status.sites) - sum(1 for s in status.sites if s.healthy)
        issues += len(status.stale_ghosts) + len(status.memory_alerts)
        console.print(Panel(f"[bold red]⚠️  {issues} ISSUE(S) DETECTED[/]", border_style="red"))

    sys.exit(0 if status.all_healthy else 1)


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON for automation")
def status(as_json: bool) -> None:
    """Show last check results."""
    last = MoskvDaemon.load_status()
    if not last:
        if as_json:
            click.echo('{"error": "no status found"}')
        else:
            console.print("[yellow]No daemon status found. Run 'moskv-daemon check' first.[/]")
        sys.exit(1)

    # JSON mode: dump and exit
    if as_json:
        import json

        # Enrich with telemetry if available
        try:
            from cortex.telemetry import collector  # type: ignore[reportAttributeAccessIssue]

            last["telemetry"] = {
                "spans_total": len(collector),
                "spans_recent": [
                    {"name": s.name, "duration_ms": round(s.duration_ms, 1), "ok": s.ok}
                    for s in collector.spans[-10:]
                ],
            }
        except ImportError:
            pass
        click.echo(json.dumps(last, indent=2, ensure_ascii=False))
        sys.exit(0 if last.get("all_healthy") else 1)

    # Rich table mode (existing behavior)
    table = Table(title="MOSKV-1 — Last Status", show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Checked at", last.get("checked_at", "unknown"))
    table.add_row("Duration", f"{last.get('check_duration_ms', 0):.0f}ms")
    table.add_row("All healthy", "✅ Yes" if last.get("all_healthy") else "❌ No")

    sites = last.get("sites", [])
    for s in sites:
        icon = "🟢" if s.get("healthy") else "🔴"
        table.add_row(f"  {icon} {s.get('url', '?')}", f"{s.get('response_ms', 0):.0f}ms")

    ghosts = last.get("stale_ghosts", [])
    for g in ghosts:
        table.add_row(f"  💤 {g.get('project', '?')}", f"{g.get('hours_stale', 0):.0f}h stale")

    alerts = last.get("memory_alerts", [])
    for m in alerts:
        table.add_row(f"  ⚠️  {m.get('file', '?')}", f"{m.get('hours_stale', 0):.0f}h stale")

    errors = last.get("errors", [])
    for e in errors:
        table.add_row("  ❌ Error", str(e))

    console.print(table)


@cli.command()
def version() -> None:
    """Show CORTEX / MOSKV-1 version."""
    console.print(f"[bold cyan]MOSKV-1 Daemon[/] — CORTEX v{__version__}")


@cli.command()
def install() -> None:
    """Install daemon as a system service (launchd / systemd / Task Scheduler)."""
    from cortex.extensions.daemon.platform import (
        install_linux,
        install_macos,
        install_windows,
    )

    if is_macos():
        install_macos()
    elif is_linux():
        install_linux()
    elif is_windows():
        install_windows()
    else:
        console.print(f"[red]❌ Unsupported platform: {sys.platform}[/]")
        sys.exit(1)


@cli.command()
def uninstall() -> None:
    """Remove daemon system service."""
    from cortex.extensions.daemon.platform import (
        uninstall_linux,
        uninstall_macos,
        uninstall_windows,
    )

    if is_macos():
        uninstall_macos()
    elif is_linux():
        uninstall_linux()
    elif is_windows():
        uninstall_windows()
    else:
        console.print(f"[red]❌ Unsupported platform: {sys.platform}[/]")
        sys.exit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
