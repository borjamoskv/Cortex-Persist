"""
CORTEX v4.0 — Episodic Memory CLI Commands.

CLI interface for recording, recalling, and analyzing episodic memories.
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli import DEFAULT_DB, get_engine

console = Console()


@click.group()
def episode():
    """Episodic Memory — persistent native memory."""
    pass


# ─── Record ──────────────────────────────────────────────────────────


@episode.command("record")
@click.argument("content")
@click.option("--project", "-p", default=None, help="Project name")
@click.option(
    "--type",
    "event_type",
    default="decision",
    type=click.Choice(
        [
            "decision",
            "error",
            "discovery",
            "flow_state",
            "insight",
            "milestone",
            "blocked",
            "resolved",
        ]
    ),
    help="Event type",
)
@click.option("--emotion", "-e", default="neutral", help="Emotional state")
@click.option("--session", "-s", default=None, help="Session ID (auto-generated if omitted)")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def record_cmd(
    content: str,
    project: str | None,
    event_type: str,
    emotion: str,
    session: str | None,
    tags: str,
    db: str,
) -> None:
    """Record an episodic memory event."""
    asyncio.run(_record_async(content, project, event_type, emotion, session, tags, db))


async def _record_async(
    content: str,
    project: str | None,
    event_type: str,
    emotion: str,
    session: str | None,
    tags: str,
    db: str,
) -> None:
    from cortex.episodic import EpisodicMemory

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        memory = EpisodicMemory(conn)

        session_id = session or str(uuid.uuid4())[:8]
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        ep_id = await memory.record(
            session_id=session_id,
            event_type=event_type,
            content=content,
            project=project,
            emotion=emotion,
            tags=tag_list,
        )

        console.print(
            Panel(
                f"[green]Episode #{ep_id}[/green] recorded\n"
                f"[dim]Session: {session_id} | Type: {event_type} | "
                f"Project: {project or '—'}[/dim]",
                title="🧠 Episodic Memory",
            )
        )
    finally:
        await engine.close()


# ─── Recall ──────────────────────────────────────────────────────────


@episode.command("recall")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--type", "event_type", default=None, help="Filter by event type")
@click.option("--since", default=None, help="ISO timestamp or relative (e.g. '24h')")
@click.option("--search", "-q", default=None, help="Full-text search query")
@click.option("--limit", "-n", default=20, help="Max results")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall_cmd(
    project: str | None,
    event_type: str | None,
    since: str | None,
    search: str | None,
    limit: int,
    as_json: bool,
    db: str,
) -> None:
    """Recall episodic memories with flexible filtering."""
    asyncio.run(_recall_async(project, event_type, since, search, limit, as_json, db))


async def _recall_async(
    project: str | None,
    event_type: str | None,
    since: str | None,
    search: str | None,
    limit: int,
    as_json: bool,
    db: str,
) -> None:
    from cortex.episodic import EpisodicMemory

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        memory = EpisodicMemory(conn)

        # Handle relative time like "24h", "7d"
        resolved_since = _resolve_since(since) if since else None

        episodes = await memory.recall(
            project=project,
            event_type=event_type,
            since=resolved_since,
            limit=limit,
            search=search,
        )

        if as_json:
            console.print(
                json.dumps(
                    [e.to_dict() for e in episodes],
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

        if not episodes:
            console.print("[dim]No episodes found.[/dim]")
            return

        table = Table(
            title=f"🧠 Episodes ({len(episodes)})",
            show_header=True,
        )
        table.add_column("ID", style="dim", width=5)
        table.add_column("Type", style="green", width=12)
        table.add_column("Project", style="cyan", width=14)
        table.add_column("Content", width=50)
        table.add_column("Emotion", width=10)
        table.add_column("Created", style="dim", width=16)

        for ep in episodes:
            table.add_row(
                str(ep.id),
                ep.event_type,
                ep.project or "—",
                ep.content[:50],
                ep.emotion,
                ep.created_at[:16],
            )
        console.print(table)
    finally:
        await engine.close()


# ─── Patterns ────────────────────────────────────────────────────────


@episode.command("patterns")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--min-occurrences", "-m", default=2, help="Minimum sessions for a pattern")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def patterns_cmd(
    project: str | None,
    min_occurrences: int,
    as_json: bool,
    db: str,
) -> None:
    """Detect recurring patterns across sessions."""
    asyncio.run(_patterns_async(project, min_occurrences, as_json, db))


async def _patterns_async(
    project: str | None,
    min_occurrences: int,
    as_json: bool,
    db: str,
) -> None:
    from cortex.episodic import EpisodicMemory

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        memory = EpisodicMemory(conn)

        patterns = await memory.detect_patterns(
            project=project,
            min_occurrences=min_occurrences,
        )

        if as_json:
            console.print(
                json.dumps(
                    [p.to_dict() for p in patterns],
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

        if not patterns:
            console.print("[dim]No recurring patterns detected.[/dim]")
            return

        table = Table(title="🔄 Recurring Patterns", show_header=True)
        table.add_column("Theme", style="bold cyan")
        table.add_column("Sessions", justify="right")
        table.add_column("Types", style="green")
        table.add_column("Sample")

        for p in patterns:
            table.add_row(
                p.theme,
                str(p.occurrences),
                ", ".join(p.event_types[:2]),
                p.sample_content[0][:60] if p.sample_content else "—",
            )
        console.print(table)
    finally:
        await engine.close()


# ─── Boot ────────────────────────────────────────────────────────────


@episode.command("boot")
@click.option("--project", "-p", default=None, help="Focus on project")
@click.option("--top-k", "-k", default=10, help="Number of recent episodes")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def boot_cmd(
    project: str | None,
    top_k: int,
    as_json: bool,
    db: str,
) -> None:
    """Generate session boot payload (replaces context-snapshot.md)."""
    asyncio.run(_boot_async(project, top_k, as_json, db))


async def _boot_async(
    project: str | None,
    top_k: int,
    as_json: bool,
    db: str,
) -> None:
    from cortex.episodic_boot import generate_session_boot

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        payload = await generate_session_boot(
            conn=conn,
            project_hint=project,
            top_k=top_k,
        )

        if as_json:
            console.print(
                json.dumps(
                    payload.to_dict(),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            console.print(payload.to_markdown())
    finally:
        await engine.close()


# ─── Helpers ─────────────────────────────────────────────────────────


def _resolve_since(value: str) -> str:
    """Resolve relative time expressions to ISO timestamps.

    Supports: '24h', '7d', '1w', or pass-through ISO strings.
    """
    match = re.match(r"^(\d+)\s*([hdw])$", value.strip().lower())
    if not match:
        return value  # Assume ISO

    amount = int(match.group(1))
    unit = match.group(2)

    delta_map = {
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }
    cutoff = datetime.now(timezone.utc) - delta_map[unit]
    return cutoff.strftime("%Y-%m-%dT%H:%M:%S")


# ─── Observe ─────────────────────────────────────────────────────────


@episode.command("observe")
@click.option("--workspace", "-w", default=".", help="Workspace path to observe")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def observe_cmd(
    workspace: str,
    db: str,
) -> None:
    """Start the real-time perception observer in the foreground."""
    asyncio.run(_observe_async(workspace, db))


async def _observe_async(
    workspace: str,
    db: str,
) -> None:
    import os

    from cortex.perception import PerceptionPipeline

    workspace_path = os.path.abspath(workspace)
    if not os.path.exists(workspace_path):
        console.print(f"[red]Error:[/red] Workspace path {workspace_path} does not exist.")
        return

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        session_id = f"cli-observe-{uuid.uuid4().hex[:8]}"
        pipeline = PerceptionPipeline(
            conn=conn, session_id=session_id, workspace=workspace_path, window_s=300, cooldown_s=300
        )

        console.print(
            Panel(
                f"[green]Starting Perception Observer[/green]\nWorkspace: {workspace_path}\nSession ID: {session_id}",
                title="👁️ Real-Time Perception",
            )
        )

        pipeline.start()

        console.print("[dim]Monitoring file activity... Press Ctrl+C to stop.[/dim]")

        try:
            while True:
                await asyncio.sleep(30)
                snapshot = await pipeline.tick()
                if snapshot:
                    if snapshot.confidence in ("C4", "C5"):
                        console.print(
                            f"[cyan]👁️ Pattern Detected:[/cyan] [bold]{snapshot.intent}[/bold] ({snapshot.confidence}) on {snapshot.project or 'workspace'} - {snapshot.emotion}"
                        )
                        console.print(f"   [dim]{snapshot.summary}[/dim]")
                    else:
                        console.print(
                            f"[dim]Activity level: {snapshot.event_count} events in last 5 min[/dim]"
                        )
        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping observer...[/yellow]")
        finally:
            pipeline.stop()

    finally:
        await engine.close()
