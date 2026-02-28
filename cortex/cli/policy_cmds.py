"""CORTEX CLI — Policy Engine commands.

`cortex policy` — Bellman-scored action prioritization.
"""

from __future__ import annotations

import click
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    _run_async,
    close_engine_sync,
    console,
    get_engine,
)


@click.group("policy")
def policy_cmds() -> None:
    """🎯 Bellman Policy Engine — Prioritized action queue."""
    pass


@policy_cmds.command("evaluate")
@click.option("--project", "-p", default=None, help="Scope to a single project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--limit", "-n", default=20, help="Max actions to show")
@click.option("--gamma", "-g", default=0.9, type=float, help="Discount factor (0-1)")
def evaluate_cmd(project: str | None, db: str, limit: int, gamma: float) -> None:
    """Evaluate memory and output prioritized action queue."""
    from cortex.policy import PolicyConfig, PolicyEngine

    engine = get_engine(db)
    try:
        _run_async(engine.init_db())
        config = PolicyConfig(gamma=gamma, max_actions=limit)
        policy = PolicyEngine(engine, config)
        actions = _run_async(policy.evaluate(project=project))

        if not actions:
            console.print("[dim]No actionable items found.[/dim]")
            return

        table = Table(
            title="🎯 CORTEX Policy Engine — Action Queue",
            title_style="bold #CCFF00",
            border_style="#2E5090",
            show_lines=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Value", style="bold #CCFF00", width=7)
        table.add_column("Type", style="#6600FF", width=16)
        table.add_column("Project", style="#D4AF37", width=16)
        table.add_column("Description", style="white", max_width=60)

        for i, action in enumerate(actions, 1):
            # Color-code value.
            v = action.value
            if v > 0.7:
                v_color = "bold red"
            elif v > 0.4:
                v_color = "bold yellow"
            else:
                v_color = "dim"
            table.add_row(
                str(i),
                f"[{v_color}]{v:.3f}[/{v_color}]",
                action.action_type,
                action.project,
                action.description[:80],
            )

        console.print(table)
        console.print(
            f"\n[dim]γ={gamma} | {len(actions)} actions | "
            f"V(s) = R(s,a) + γ·V(s')[/dim]"
        )

    finally:
        close_engine_sync(engine)


# Alias: `cortex policy` without subcommand runs evaluate.
@policy_cmds.command("status")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def status_cmd(db: str) -> None:
    """Show policy engine status and configuration."""
    from cortex.policy import PolicyConfig

    config = PolicyConfig()
    console.print("[bold #CCFF00]Policy Engine Config[/bold #CCFF00]")
    console.print(f"  γ (gamma):            {config.gamma}")
    console.print(f"  Blocking multiplier:  {config.blocking_multiplier}")
    console.print(f"  Cross-project bonus:  {config.cross_project_bonus}")
    console.print(f"  Error recency weight: {config.error_recency_weight}")
    console.print(f"  Ghost age decay:      {config.ghost_age_decay}")
    console.print(f"  Max actions:          {config.max_actions}")
    console.print(f"  Recency window:       {config.recency_window_hours}h")
