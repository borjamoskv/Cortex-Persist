# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import subprocess
import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.engine.entropy_core import EntropyCore
from cortex.guards.entropy_guard import EntropyGuardEngine, GuardAction
from cortex.engine.decision_engine import DecisionEngine


@click.group("gateway")
def gateway_cmds() -> None:
    """CORTEX gateway management commands."""


@gateway_cmds.command("health")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def health(db: str, as_json: bool) -> None:
    """Check gateway resonance and health."""
    # For now, it mirrors global health or specific gateway metrics if available
    from cortex.extensions.health import HealthCollector, HealthScorer

    engine = get_engine(db)
    collector = HealthCollector(db_path=db)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    if as_json:
        out = {
            "status": "healthy" if hs.score > 80 else "degraded",
            "score": hs.score,
            "grade": hs.grade.letter,
            "timestamp": hs.timestamp,
        }
        click.echo(json.dumps(out, indent=2))
        return

    console.print(
        f"\n[[noir.cyber]⚡[/]] Gateway Health: [bold]{hs.score:.1f}/100[/] ([noir.yinmn]{hs.grade.letter}[/])"
    )
    console.print(f"[dim]State: {'Resonant' if hs.score > 90 else 'Stable'}[/]\n")
    engine.close_sync()


cli.add_command(gateway_cmds)

@gateway_cmds.command("evaluate")
@click.option("--diff", default="HEAD~1", help="Git reference to compare against")
@click.option("--intent", default="", help="The original prompt/intent used to generate the change")
def evaluate(diff: str, intent: str) -> None:
    """Evaluates the entropy of the current changes against a git reference."""
    workspace_root = os.getcwd()
    
    try:
        diff_cmd = ["git", "diff", diff]
        diff_output = subprocess.check_output(diff_cmd, text=True)
        
        files_cmd = ["git", "diff", "--name-only", diff]
        modified_files = subprocess.check_output(files_cmd, text=True).splitlines()
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to execute git diff: {e}[/bold red]")
        exit(1)

    if not modified_files:
        console.print("[bold yellow]No modified files found. Entropy delta is zero.[/bold yellow]")
        exit(0)

    console.print(f"[bold blue]Evaluating Entropy Delta for {len(modified_files)} files...[/bold blue]")

    core = EntropyCore(workspace_root)
    guard = EntropyGuardEngine()
    decision = DecisionEngine()

    state = core.evaluate_entropy(diff_content=diff_output, intent_prompt=intent, modified_files=modified_files)
    guard_decision = guard.evaluate(state)
    resolution = decision.resolve(state, guard_decision)

    table = Table(title="CORTEX Entropy State", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Structural Entropy", f"{state.structural:.3f}")
    table.add_row("Semantic Drift", f"{state.semantic:.3f}")
    table.add_row("Operational Entropy", f"{state.operational:.3f}")
    table.add_row("Total System Entropy", f"{state.total:.3f}")
    table.add_row("Regime", f"{state.regime.value}")
    
    console.print(table)

    color = "green" if resolution.action == GuardAction.ALLOW else "red" if resolution.action == GuardAction.BLOCK else "yellow"
    
    panel = Panel(
        f"[bold {color}]ACTION: {resolution.action.value}[/bold {color}]\n\n{resolution.feedback}",
        title="Policy Resolution",
        border_style=color
    )
    console.print(panel)

    if resolution.action == GuardAction.BLOCK:
        console.print("\n[bold red]MERGE BLOCKED due to critical entropy delta.[/bold red]")
        exit(1)
    else:
        exit(0)
