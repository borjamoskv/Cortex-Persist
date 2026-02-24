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
    chronos_cmds,  # noqa: E402, F401
    compact_cmds,  # noqa: E402, F401
    context_cmds,  # noqa: E402, F401
    core,  # noqa: E402, F401
    crud,  # noqa: E402, F401
    entropy_cmds,  # noqa: E402, F401
    episodic_cmds,  # noqa: E402, F401
    episodic_observe,  # noqa: E402, F401
    handoff_cmds,  # noqa: E402, F401
    launchpad_cmds,  # noqa: E402, F401
    mejoralo_cmds,  # noqa: E402, F401
    nexus_cmds,  # noqa: E402, F401
    prompt_cmds,  # noqa: E402, F401  — Prompt generation
    purge,  # noqa: E402, F401
    reflect_cmds,  # noqa: E402, F401  — Reflection System
    sync_cmds,  # noqa: E402, F401
    time_cmds,  # noqa: E402, F401
    timeline_cmds,  # noqa: E402, F401
    tips_cmds,  # noqa: E402, F401  — TIPS System
    trust_cmds,  # noqa: E402, F401  — Trust & Compliance
    vote_ledger,  # noqa: E402, F401
)
from cortex.cli.chronos_cmds import chronos_cmds as chronos_cli  # noqa: E402
from cortex.cli.compact_cmds import (  # noqa: E402
    compact_cmd,
    compact_session_cmd,
    compact_status,
)
from cortex.cli.context_cmds import context  # noqa: E402
from cortex.cli.entropy_cmds import entropy  # noqa: E402
from cortex.cli.episodic_cmds import episode  # noqa: E402
from cortex.cli.episodic_observe import run_observe  # noqa: E402
from cortex.cli.handoff_cmds import handoff as handoff_cli  # noqa: E402
from cortex.cli.launchpad_cmds import launchpad  # noqa: E402
from cortex.cli.mejoralo_cmds import mejoralo  # noqa: E402
from cortex.cli.reflect_cmds import inject as inject_cmd  # noqa: E402
from cortex.cli.reflect_cmds import reflect as reflect_cmd  # noqa: E402
from cortex.cli.swarm_cmds import swarm  # noqa: E402
from cortex.cli.sync_cmds import (  # noqa: E402
    export,
    obsidian,
    writeback,
)
from cortex.cli.sync_cmds import sync as sync_cmd  # noqa: E402

# ─── Registro de comandos ───────────────────────────────────────────────
from cortex.cli.time_cmds import heartbeat_cmd, time_cmd  # noqa: E402
from cortex.cli.timeline_cmds import timeline  # noqa: E402
from cortex.cli.tips_cmds import tips  # noqa: E402
from cortex.cli.trust_cmds import (  # noqa: E402
    audit_trail,
    compliance_report,
    verify_fact,
)
from cortex.cli.vote_ledger import ledger  # noqa: E402

cli.add_command(time_cmd, name="time")
cli.add_command(heartbeat_cmd, name="heartbeat")
cli.add_command(compact_cmd, name="compact")
cli.add_command(compact_status, name="compact-status")
cli.add_command(compact_session_cmd, name="compact-session")
cli.add_command(ledger)
cli.add_command(timeline)
cli.add_command(launchpad)
cli.add_command(launchpad, name="mission")  # Alias por compatibilidad
cli.add_command(mejoralo)
cli.add_command(context)
cli.add_command(entropy)
cli.add_command(tips)
cli.add_command(swarm)
cli.add_command(chronos_cli, name="chronos")
cli.add_command(handoff_cli, name="handoff")
cli.add_command(reflect_cmd, name="reflect")
cli.add_command(inject_cmd, name="inject")
cli.add_command(sync_cmd, name="sync")
cli.add_command(export)
cli.add_command(writeback)
cli.add_command(obsidian)
cli.add_command(verify_fact, name="verify")
cli.add_command(compliance_report, name="compliance")
cli.add_command(audit_trail, name="audit")
from cortex.cli.apotheosis_cmds import apotheosis_cmds as apotheosis_cli  # noqa: E402
from cortex.cli.autorouter_cmds import autorouter_cmds as autorouter_cli  # noqa: E402
from cortex.cli.ghost_cmds import ghost_cmds as ghost_cli  # noqa: E402
from cortex.cli.keter_cmds import keter_cmds as keter_cli  # noqa: E402
from cortex.cli.nexus_cmds import nexus_cmds as nexus_cli  # noqa: E402
from cortex.cli.prompt_cmds import prompt as prompt_group  # noqa: E402
from cortex.cli.purge import purge as purge_cmd  # noqa: E402

cli.add_command(ghost_cli, name="ghost")
cli.add_command(nexus_cli, name="nexus")
cli.add_command(autorouter_cli, name="autorouter")
cli.add_command(apotheosis_cli, name="apotheosis")
cli.add_command(keter_cli, name="keter")
cli.add_command(episode)
cli.add_command(purge_cmd, name="purge")
cli.add_command(prompt_group, name="prompt")


@cli.command("observe")
@click.option("--workspace", "-w", default=".", help="Workspace path to observe")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def observe_cmd(workspace, db):
    """Start real-time perception observer."""
    run_observe(workspace, db, console)


if __name__ == "__main__":
    cli()
