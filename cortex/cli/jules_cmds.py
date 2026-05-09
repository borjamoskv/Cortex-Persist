"""cortex jules — CLI commands for Jules bridge.

Direct terminal interface to dispatch tasks, check status, and
communicate with Jules sessions from the command line.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger("cortex.cli.jules")
console = Console()


@click.group("jules")
def jules_cli() -> None:
    """🤖 Jules Bridge — Communicate with Google Jules AI agent."""


@jules_cli.command("dispatch")
@click.argument("prompt")
@click.option("--owner", default="borjamoskv", help="GitHub repo owner")
@click.option("--repo", default="Cortex-Persist", help="GitHub repo name")
@click.option("--branch", default="main", help="Starting branch")
@click.option("--title", default=None, help="Session title")
@click.option("--auto-approve", is_flag=True, help="Skip plan approval requirement")
def cmd_dispatch(
    prompt: str,
    owner: str,
    repo: str,
    branch: str,
    title: str | None,
    auto_approve: bool,
) -> None:
    """Dispatch a coding task to Jules."""
    from cortex.gateway.jules import JulesClient, source_from_repo

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.create_session(
                prompt=prompt,
                source=source_from_repo(owner, repo),
                branch=branch,
                title=title,
                require_plan_approval=not auto_approve,
            )

    try:
        result = asyncio.run(_run())
        session_name = result.get("name", "unknown")
        session_id = session_name.rsplit("/", 1)[-1] if "/" in session_name else session_name

        console.print(
            Panel(
                f"[bold green]Session created[/]\n\n"
                f"  ID:     [cyan]{session_id}[/]\n"
                f"  State:  {result.get('state', 'UNKNOWN')}\n"
                f"  URL:    [link]https://jules.google.com/session/{session_id}[/link]\n"
                f"  Prompt: {prompt[:100]}",
                title="🤖 Jules → Dispatched",
                border_style="blue",
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("status")
@click.argument("session_id")
def cmd_status(session_id: str) -> None:
    """Check status of a Jules session."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.get_session(session_id)

    try:
        result = asyncio.run(_run())
        state = result.get("state", "UNKNOWN")
        state_color = {
            "COMPLETED": "green",
            "FAILED": "red",
            "CANCELLED": "yellow",
        }.get(state, "cyan")

        console.print(
            Panel(
                f"  State:  [{state_color}]{state}[/]\n"
                f"  Title:  {result.get('title', 'N/A')}\n"
                f"  Prompt: {result.get('prompt', 'N/A')[:120]}",
                title=f"🤖 Jules Session {session_id}",
                border_style="blue",
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("list")
@click.option("--limit", default=10, help="Number of sessions to show")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def cmd_list(limit: int, json_output: bool) -> None:
    """List recent Jules sessions."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.list_sessions(page_size=limit)

    try:
        result = asyncio.run(_run())
        sessions = result.get("sessions", [])

        if json_output:
            click.echo(json.dumps(sessions, indent=2))
            return

        if not sessions:
            console.print("[dim]No sessions found.[/]")
            return

        table = Table(title="Jules Sessions", border_style="blue")
        table.add_column("ID", style="cyan", max_width=24)
        table.add_column("State", style="bold")
        table.add_column("Title", max_width=30)
        table.add_column("Prompt", max_width=50)

        for s in sessions:
            name = s.get("name", "")
            sid = name.rsplit("/", 1)[-1] if "/" in name else name
            state = s.get("state", "?")
            state_styled = {
                "COMPLETED": f"[green]{state}[/]",
                "FAILED": f"[red]{state}[/]",
            }.get(state, state)

            table.add_row(
                sid[:24],
                state_styled,
                s.get("title", "")[:30],
                s.get("prompt", "")[:50],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("send")
@click.argument("session_id")
@click.argument("message")
def cmd_send(session_id: str, message: str) -> None:
    """Send a message to an active Jules session."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.send_message(session_id, message)

    try:
        asyncio.run(_run())
        console.print(f"[green]✓[/] Message sent to session [cyan]{session_id}[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("approve")
@click.argument("session_id")
def cmd_approve(session_id: str) -> None:
    """Approve a pending plan in a Jules session."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.approve_plan(session_id)

    try:
        asyncio.run(_run())
        console.print(f"[green]✓[/] Plan approved for session [cyan]{session_id}[/]")
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("activities")
@click.argument("session_id")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def cmd_activities(session_id: str, json_output: bool) -> None:
    """View activity log for a Jules session."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.list_activities(session_id)

    try:
        result = asyncio.run(_run())
        activities = result.get("activities", [])

        if json_output:
            click.echo(json.dumps(activities, indent=2))
            return

        if not activities:
            console.print("[dim]No activities found.[/]")
            return

        for i, act in enumerate(activities, 1):
            kind = act.get("type", act.get("kind", "unknown"))
            content = act.get("content", act.get("message", ""))
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)[:200]
            console.print(f"  [dim]{i}.[/] [{kind}] {str(content)[:120]}")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@jules_cli.command("poll")
@click.argument("session_id")
@click.option("--timeout", default=600, help="Timeout in seconds")
@click.option("--interval", default=15, help="Poll interval in seconds")
def cmd_poll(session_id: str, timeout: int, interval: int) -> None:
    """Wait for a Jules session to complete."""
    from cortex.gateway.jules import JulesClient

    async def _run() -> dict:
        async with JulesClient() as client:
            return await client.wait_for_completion(
                session_id,
                poll_interval_s=float(interval),
                timeout_s=float(timeout),
            )

    console.print(f"[dim]Polling session {session_id} (timeout={timeout}s)...[/]")
    try:
        result = asyncio.run(_run())
        state = result.get("state", "UNKNOWN")
        console.print(f"[bold green]Session completed:[/] {state}")
    except TimeoutError:
        console.print(f"[red]Session {session_id} did not complete within {timeout}s[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

from cortex.cli.common import cli
cli.add_command(jules_cli)
