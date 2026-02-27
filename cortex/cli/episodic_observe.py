"""
CORTEX v5.0 — Episodic Memory: Observe Command.

Extracted from episodic_cmds.py to keep file size under 300 LOC.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from rich.panel import Panel

from cortex.cli.common import get_engine

__all__ = ["run_observe"]


def run_observe(workspace: str, db: str, console) -> None:
    """Start the real-time perception observer in the foreground."""
    asyncio.run(_observe_async(workspace, db, console))


async def _observe_async(workspace: str, db: str, console) -> None:
    from cortex.perception import PerceptionPipeline

    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists():
        console.print(
            Panel(
                f"[bold red]Workspace no encontrado[/]\n\n"
                f"  Ruta: [dim]{workspace_path}[/dim]\n\n"
                f"[yellow]¿Cómo resolverlo?[/]\n"
                f"  Usa [cyan]--workspace /ruta/correcta[/cyan] o ejecuta desde el directorio del proyecto.",
                title="📁 CORTEX — Workspace No Encontrado",
                border_style="red",
            )
        )
        return

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        session_id = f"cli-observe-{uuid.uuid4().hex[:8]}"
        pipeline = PerceptionPipeline(
            conn=conn,
            session_id=session_id,
            workspace=str(workspace_path),
            window_s=300,
            cooldown_s=300,
        )

        console.print(
            Panel(
                f"[green]Starting Perception Observer[/green]\n"
                f"Workspace: {workspace_path}\n"
                f"Session ID: {session_id}",
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
                            f"[cyan]👁️ Pattern Detected:[/cyan] "
                            f"[bold]{snapshot.intent}[/bold] "
                            f"({snapshot.confidence}) on "
                            f"{snapshot.project or 'workspace'} - "
                            f"{snapshot.emotion}"
                        )
                        console.print(f"   [dim]{snapshot.summary}[/dim]")
                    else:
                        console.print(
                            f"[dim]Activity level: {snapshot.event_count} "
                            f"events in last 5 min[/dim]"
                        )
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping observer...[/yellow]")
        finally:
            pipeline.stop()

    finally:
        await engine.close()
