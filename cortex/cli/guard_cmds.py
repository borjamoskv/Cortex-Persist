"""CORTEX CLI — Guard Daemon commands.

`cortex guard` — Sovereign governance daemon for AI agent actions.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import click
from rich.table import Table

from cortex.cli.common import console


@click.group("guard")
def guard_cmds() -> None:
    """🛡️ Guard Daemon — Sovereign governance for AI agents."""


@guard_cmds.command("start")
@click.option(
    "--path",
    "-p",
    default=".",
    help="Directory to watch (default: cwd)",
)
@click.option(
    "--policy",
    default="cortex.policy.yaml",
    help="Policy file path",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all verdicts including PASS",
)
@click.option(
    "--foreground",
    "-f",
    is_flag=True,
    help="Run in foreground (don't daemonize)",
)
@click.option(
    "--db",
    default=None,
    help="Ledger database path for verdict persistence",
)
def start_cmd(
    path: str,
    policy: str,
    verbose: bool,
    foreground: bool,
    db: str | None,
) -> None:
    """Start the Guard Daemon."""
    from cortex.daemon.guard_daemon import GuardDaemon

    # Check if already running
    if GuardDaemon.is_daemon_running():
        pid = GuardDaemon.read_pid()
        console.print(f"[bold yellow]⚠ Guard daemon already running (PID {pid})[/bold yellow]")
        return

    daemon = GuardDaemon(
        watch_path=path,
        policy_path=policy,
        quiet=not verbose,
        ledger_db=db,
    )

    if foreground:
        # Run in foreground (blocks)
        try:
            import asyncio

            asyncio.run(daemon.run())
        except KeyboardInterrupt:
            console.print("\n[dim]Guard daemon stopped.[/dim]")
    else:
        # Fork to background
        _daemonize(daemon, path, policy, verbose, db)


def _daemonize(
    daemon: object,
    path: str,
    policy: str,
    verbose: bool,
    db: str | None,
) -> None:
    """Fork the daemon process to background."""
    pid = os.fork()
    if pid > 0:
        # Parent: report and exit
        console.print(
            f"[bold #CCFF00]🛡️ Guard Daemon started[/bold #CCFF00] "
            f"(PID {pid}) watching {Path(path).resolve()}"
        )
        console.print("[dim]Use `cortex guard status` to check, `cortex guard stop` to halt[/dim]")
        return

    # Child: detach and run
    os.setsid()

    # Redirect stdout/stderr to log
    log_dir = Path.home() / ".cortex"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / "guard_daemon.log", "a", encoding="utf-8")  # noqa: SIM115
    os.dup2(log_file.fileno(), sys.stdout.fileno())
    os.dup2(log_file.fileno(), sys.stderr.fileno())

    # Re-create daemon in child process
    from cortex.daemon.guard_daemon import GuardDaemon

    child_daemon = GuardDaemon(
        watch_path=path,
        policy_path=policy,
        quiet=not verbose,
        ledger_db=db,
    )

    import asyncio

    try:
        asyncio.run(child_daemon.run())
    except Exception:  # noqa: S110
        pass
    finally:
        sys.exit(0)


@guard_cmds.command("stop")
def stop_cmd() -> None:
    """Stop the Guard Daemon."""
    from cortex.daemon.guard_daemon import GuardDaemon

    if not GuardDaemon.is_daemon_running():
        console.print("[dim]No guard daemon running.[/dim]")
        return

    pid = GuardDaemon.read_pid()
    if GuardDaemon.stop_daemon():
        console.print(f"[bold #CCFF00]🛡️ Guard Daemon stopped[/bold #CCFF00] (PID {pid})")
        # Wait briefly for cleanup
        time.sleep(0.5)
        if GuardDaemon.is_daemon_running():
            console.print("[dim]Daemon still shutting down...[/dim]")
    else:
        console.print("[bold red]Failed to stop daemon[/bold red]")


@guard_cmds.command("status")
def status_cmd() -> None:
    """Show Guard Daemon status and recent verdicts."""
    from cortex.daemon.guard_daemon import GuardDaemon
    from cortex.daemon.verdict_emitter import _DEFAULT_LOG

    is_running = GuardDaemon.is_daemon_running()
    pid = GuardDaemon.read_pid()

    # Status header
    if is_running:
        console.print(f"[bold #CCFF00]🛡️ Guard Daemon: ACTIVE[/bold #CCFF00] (PID {pid})")
    else:
        console.print("[dim]🛡️ Guard Daemon: INACTIVE[/dim]")

    # Read recent verdicts from log
    if _DEFAULT_LOG.exists():
        lines = _DEFAULT_LOG.read_text(encoding="utf-8").strip().split("\n")
        recent = lines[-10:] if len(lines) > 10 else lines

        if recent and recent[0]:
            table = Table(
                title="Recent Verdicts",
                title_style="bold",
                border_style="#2E5090",
                show_lines=False,
            )
            table.add_column("Verdict", style="bold", width=12)
            table.add_column("Type", style="#6600FF", width=16)
            table.add_column("Path", max_width=40)
            table.add_column("Rule", style="dim", width=20)

            for line in recent:
                try:
                    entry = json.loads(line)
                    verdict = entry.get("verdict", "?")
                    if verdict == "CORTEX_BLOCK":
                        v_style = "bold red"
                    elif verdict == "CORTEX_WARN":
                        v_style = "bold yellow"
                    else:
                        v_style = "bold green"

                    table.add_row(
                        f"[{v_style}]{verdict.replace('CORTEX_', '')}[/{v_style}]",
                        entry.get("action_type", "?"),
                        entry.get("path", "")[:40],
                        entry.get("rule_id", ""),
                    )
                except json.JSONDecodeError:
                    continue

            console.print(table)
        else:
            console.print("[dim]No verdicts recorded yet.[/dim]")
    else:
        console.print("[dim]No verdict log found.[/dim]")


@guard_cmds.command("log")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def log_cmd(lines: int, follow: bool) -> None:
    """Tail the guard verdict log."""
    from cortex.daemon.verdict_emitter import _DEFAULT_LOG

    if not _DEFAULT_LOG.exists():
        console.print(f"[dim]No guard log found at {_DEFAULT_LOG}[/dim]")
        return

    # Read last N lines
    all_lines = _DEFAULT_LOG.read_text(encoding="utf-8").strip().split("\n")
    tail = all_lines[-lines:] if len(all_lines) > lines else all_lines

    for line in tail:
        try:
            entry = json.loads(line)
            verdict = entry.get("verdict", "?").replace("CORTEX_", "")
            ts = time.strftime(
                "%H:%M:%S",
                time.localtime(entry.get("timestamp", 0)),
            )
            path = entry.get("path", "")
            detail = entry.get("detail", "")

            if verdict == "BLOCK":
                console.print(f"[bold red]{ts} ✗ {verdict}[/bold red] {path} {detail}")
            elif verdict == "WARN":
                console.print(f"[bold yellow]{ts} ⚠ {verdict}[/bold yellow] {path} {detail}")
            else:
                console.print(f"[dim]{ts} ✓ {verdict} {path} {detail}[/dim]")
        except json.JSONDecodeError:
            continue

    if follow:
        console.print("[dim]Following... (Ctrl+C to stop)[/dim]")
        _follow_log(_DEFAULT_LOG)


def _follow_log(log_path: Path) -> None:
    """Tail -f equivalent for the guard log."""
    with open(log_path, encoding="utf-8") as f:
        f.seek(0, 2)  # Go to end
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue
                try:
                    entry = json.loads(line.strip())
                    verdict = entry.get("verdict", "?").replace("CORTEX_", "")
                    ts = time.strftime(
                        "%H:%M:%S",
                        time.localtime(entry.get("timestamp", 0)),
                    )
                    path = entry.get("path", "")
                    console.print(f"[dim]{ts}[/dim] {verdict} {path}")
                except json.JSONDecodeError:
                    pass
        except KeyboardInterrupt:
            pass


@guard_cmds.command("evaluate")
@click.argument("path")
def evaluate_cmd(path: str) -> None:
    """Evaluate a single file against the guard policy."""
    from cortex.daemon.guard_daemon import GuardDaemon

    daemon = GuardDaemon(quiet=False)
    daemon._load_policy()
    daemon._init_components()

    verdict = daemon.process_file_event(path)
    if verdict:
        console.print(f"\n[dim]Hash: {verdict.report.hash}[/dim]")
