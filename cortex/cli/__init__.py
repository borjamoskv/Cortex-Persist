"""
CORTEX CLI — Package init.

Re-exports the main CLI group and shared utilities.
"""

import click
from rich.console import Console

from cortex import __version__
from cortex.config import DEFAULT_DB_PATH
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

console = Console()
DEFAULT_DB = str(DEFAULT_DB_PATH)


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance."""
    return CortexEngine(db_path=db)


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine."""
    return TimingTracker(engine._get_conn())


# ─── Main Group ──────────────────────────────────────────────────


@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli() -> None:
    """CORTEX — Trust Infrastructure for Autonomous AI."""
    pass


# ─── Registrar todos los sub-módulos ───────────────────────────────────
from cortex.cli import (  # noqa: E402
    context_cmds,  # noqa: E402, F401
    core,  # noqa: E402, F401
    crud,  # noqa: E402, F401
    handoff_cmds,  # noqa: E402, F401
    launchpad_cmds,  # noqa: E402, F401
    mejoralo_cmds,  # noqa: E402, F401
    nexus_cmds,  # noqa: E402, F401
    purge,  # noqa: E402, F401
    reflect_cmds,  # noqa: E402, F401  — Reflection System
    sync_cmds,  # noqa: E402, F401
    time_cmds,  # noqa: E402, F401
    timeline_cmds,  # noqa: E402, F401
    tips_cmds,  # noqa: E402, F401  — TIPS System
    trust_cmds,  # noqa: E402, F401  — Trust & Compliance
    vote_ledger,  # noqa: E402, F401
)
from cortex.cli.context_cmds import context  # noqa: E402
from cortex.cli.entropy_cmds import entropy  # noqa: E402
from cortex.cli.launchpad_cmds import launchpad  # noqa: E402
from cortex.cli.mejoralo_cmds import mejoralo  # noqa: E402

# ─── Registro de comandos ───────────────────────────────────────────────
from cortex.cli.time_cmds import heartbeat_cmd, time_cmd  # noqa: E402
from cortex.cli.timeline_cmds import timeline  # noqa: E402
from cortex.cli.tips_cmds import tips  # noqa: E402
from cortex.cli.vote_ledger import ledger  # noqa: E402

cli.add_command(time_cmd, name="time")
cli.add_command(heartbeat_cmd, name="heartbeat")
cli.add_command(ledger)
cli.add_command(timeline)
cli.add_command(launchpad)
cli.add_command(launchpad, name="mission")  # Alias por compatibilidad
cli.add_command(mejoralo)
cli.add_command(context)
cli.add_command(entropy)
cli.add_command(tips)
from cortex.cli.apotheosis_cmds import apotheosis_cmds as apotheosis_cli  # noqa: E402
from cortex.cli.autorouter_cmds import autorouter_cmds as autorouter_cli  # noqa: E402
from cortex.cli.episodic_cmds import episode  # noqa: E402
from cortex.cli.nexus_cmds import nexus_cmds as nexus_cli  # noqa: E402

cli.add_command(nexus_cli, name="nexus")
cli.add_command(autorouter_cli, name="autorouter")
cli.add_command(apotheosis_cli, name="apotheosis")
cli.add_command(episode)

if __name__ == "__main__":
    cli()
