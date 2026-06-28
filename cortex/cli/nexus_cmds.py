# [C5-REAL] Exergy-Maximized
import sqlite3
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from cortex.cli.common import cli
from cortex.cli.errors import err_execution_failed, err_skill_not_found

__all__ = [
    "auto_sync_cmd",
    "bind_cmd",
    "pulse",
    "run_nexus_skill",
]

console = Console()

# Path to the Sovereign Singularity Nexus engine
NEXUS_SKILL_PATH = (
    Path.home()
    / ".gemini"
    / "antigravity"
    / "skills"
    / "singularity-nexus"
    / "scripts"
    / "singularity_engine.py"
)


def run_nexus_skill(args: list[str]):
    """Execute the singularity-nexus skill script natively streaming output."""
    if not NEXUS_SKILL_PATH.exists():
        err_skill_not_found("Singularity Nexus", str(NEXUS_SKILL_PATH))

    cmd = ["python3", str(NEXUS_SKILL_PATH)] + args

    try:
        # We don't capture output because we want Rich to render directly to the terminal
        # with full color support preserving the original aesthetics of Nexus.
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except (sqlite3.Error, OSError, RuntimeError) as e:
        err_execution_failed(" ".join(cmd), str(e))


@click.group(name="nexus")
def nexus_cmds():
    """🌌 Singularity Nexus v∞: Cross-Project Unification."""


@nexus_cmds.command()
def pulse():
    """System health audit across all MOSKV projects."""
    code = run_nexus_skill(["pulse"])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command()
def ghosts():
    """Sync ghosts across CORTEX (Handoffs) and local codebases."""
    code = run_nexus_skill(["ghosts"])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command()
@click.argument("source_project")
@click.argument("target_project")
@click.argument("pattern")
def bridge(source_project, target_project, pattern):
    """Bridge a sovereign pattern from source to target project."""
    code = run_nexus_skill(["bridge", source_project, target_project, pattern])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command("skill-sync")
def skill_sync():
    """Full unification pipeline from the Singularity Nexus Skill."""
    code = run_nexus_skill(["sync"])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command("bind")
@click.option("--target", required=True, help="Target workspace path")
@click.option("--artifact", required=True, help="Artifact path relative to CORTEX root")
def bind_cmd(target: str, artifact: str):
    """Force a physical symlink to a CORTEX artifact."""
    import os

    from cortex.extensions.nexus.symlink_engine import SymlinkEngine

    # Assumes CORTEX root is current directory or predefined
    cortex_root = os.path.abspath(os.getcwd())
    engine = SymlinkEngine(canonical_root=cortex_root)

    results = engine.propagate([target], [artifact])
    if results.get(target):
        console.print(f"[bold green]✔ Successfully bound {artifact} to {target}[/bold green]")
    else:
        console.print(f"[bold red]❌ Failed to bind {artifact} to {target}[/bold red]")


@nexus_cmds.command("auto-sync")
@click.option("--config", default="cortex_nexus_map.yaml", help="Path to Nexus configuration file")
def auto_sync_cmd(config: str):
    """Automatically propagate symlinks across all projects defined in configuration."""
    import os

    from cortex.extensions.nexus.config import load_nexus_config
    from cortex.extensions.nexus.symlink_engine import SymlinkEngine

    cortex_root = os.path.abspath(os.getcwd())
    engine = SymlinkEngine(canonical_root=cortex_root)
    conf = load_nexus_config(config)

    if not conf.target_workspaces or not conf.artifacts:
        console.print(
            f"[bold yellow]⚠️ No valid mappings found in {config}. Skipping auto-sync.[/bold yellow]"
        )
        return

    console.print(
        f"[bold magenta]🌌 Auto-Syncing {len(conf.artifacts)} artifacts to {len(conf.target_workspaces)} workspaces...[/bold magenta]"
    )
    results = engine.propagate(conf.target_workspaces, conf.artifacts)

    for workspace, success in results.items():
        if success:
            console.print(f"  [green]✔ {workspace}[/green]")
        else:
            console.print(f"  [red]❌ {workspace}[/red]")


@nexus_cmds.command("audit")
@click.option("--config", default="cortex_nexus_map.yaml", help="Path to Nexus configuration file")
def audit_cmd(config: str):
    """Audit the physical filesystem for INV_NEXUS_LINK violations."""
    import os

    from cortex.extensions.nexus.config import load_nexus_config
    from cortex.extensions.nexus.symlink_engine import SymlinkEngine

    cortex_root = os.path.abspath(os.getcwd())
    engine = SymlinkEngine(canonical_root=cortex_root)
    conf = load_nexus_config(config)

    if not conf.target_workspaces or not conf.artifacts:
        console.print(f"[bold yellow]⚠️ No valid mappings found in {config}.[/bold yellow]")
        return

    console.print(
        f"[bold cyan]🔍 Auditing {len(conf.artifacts)} artifacts across {len(conf.target_workspaces)} workspaces...[/bold cyan]"
    )
    is_valid = engine.validate_invariants(conf.target_workspaces, conf.artifacts)

    if is_valid:
        console.print(
            "[bold green]✔ INV_NEXUS_LINK strictly enforced across all queried nodes.[/bold green]"
        )
    else:
        console.print(
            "[bold red]❌ Entropy detected. One or more workspaces suffer from physical redundancy.[/bold red]"
        )
        sys.exit(1)


cli.add_command(nexus_cmds)
