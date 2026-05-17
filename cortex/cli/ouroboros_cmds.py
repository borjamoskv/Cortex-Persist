"""CORTEX Ouroboros Adversarial Testing (El Bucle Keter).

Injects simulated P0/P1 chaos (e.g. dependency mutation, secret leaks)
into a sandboxed rollback spine to ensure the Guard Daemon intercepts
the mutation in <100ms.
"""

from __future__ import annotations

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, _run_async, cli
from cortex.daemon.ouroboros import OuroborosDaemon

console = Console()
_CYBER = "bold #CCFF00"


async def _run_ouroboros(db_path: str) -> None:
    """Execute the Keter-Class Ouroboros loop."""
    console.print(f"[{_CYBER}]⧖ INITIATING OUROBOROS ADVERSARIAL TESTING (KETER-CLASS)[/]")
    daemon = OuroborosDaemon(db_path=db_path, chaos_level=1.0)
    await daemon.run_loop(interval_seconds=3)


@cli.command(name="chaos")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def chaos_cmd(db: str) -> None:
    """Run the Ouroboros Adversarial Testing Loop (Keter-Class)."""
    _run_async(_run_ouroboros(db))
