# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""
Exergy Engine CLI Commands.

CLI interface for the Exergy Daemon background loop.
"""

import asyncio
import click
from rich.panel import Panel

from cortex.cli.common import cli, console

__all__ = [
    "exergy_cmds",
]


@cli.group(name="exergy", help="⚡ Exergy - autonomous self-healing and code/health sentinel.")
def exergy_cmds() -> None:
    """El motor de salud y auto-reparación de CORTEX."""
    pass


@exergy_cmds.command("daemon")
@click.option("--interval", default=21600, type=int, help="Check interval in seconds (default: 6h)")
def run_exergy_daemon(interval: int) -> None:
    """Run the Exergy Daemon self-healing background loop."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cortex-core"))
    from exergy_daemon import ExergyDaemon

    console.print(
        Panel(
            f"[bold #2B3BE5]⚡ EXERGY DAEMON ACTIVATED[/bold #2B3BE5]\n"
            f"Frecuencia de chequeo: [italic]{interval} segundos ({interval / 3600:.1f} horas)[/italic]\n"
            f"Modo: C5-REAL Soberano",
            border_style="#2B3BE5",
        )
    )

    daemon = ExergyDaemon(check_interval=interval)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
        console.print("[yellow]Exergy Daemon stopped.[/yellow]")
