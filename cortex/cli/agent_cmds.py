"""CORTEX CLI — Agent commands (YAML-driven agent interface).

Commands:
    cortex agent run --config role.yaml   — Run an agent from YAML
    cortex agent validate --config role.yaml — Validate config
    cortex agent init                      — Generate scaffold role.yaml
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group("agent")
def agent_cmds():
    """Declarative YAML agent interface for CORTEX."""


@agent_cmds.command("init")
@click.option(
    "--output",
    "-o",
    default="role.yaml",
    help="Output path for the scaffold.",
)
def agent_init(output: str):
    """Generate a scaffold role.yaml with sensible defaults."""
    from cortex.agent.schema import AgentRole

    scaffold = AgentRole.scaffold()
    path = Path(output)
    path.write_text(scaffold.to_yaml(), encoding="utf-8")
    console.print(f"[green]✅ Scaffold written to {path}[/green]")


@agent_cmds.command("validate")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to role.yaml.",
)
def agent_validate(config: str):
    """Validate a role.yaml configuration file."""
    from cortex.agent.schema import AgentRole

    try:
        role = AgentRole.from_yaml_file(config)
    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        sys.exit(1)

    table = Table(title=f"Agent: {role.name}", show_lines=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Model", role.model)
    table.add_row("Tenant", role.tenant_id)
    table.add_row("Project", role.project_id)
    table.add_row("L1 Tokens", str(role.memory.working_memory_tokens))
    table.add_row("Session Budget", str(role.guardrails.max_session_tokens))
    table.add_row("ART ρ", f"{role.memory.art_rho:.2f}")
    table.add_row("Pruning Threshold", f"{role.memory.pruning_threshold:.2f}")
    table.add_row("Retrieval Band", role.memory.retrieval_band)
    table.add_row("Sparse Encoding", str(role.memory.sparse_encoding))
    table.add_row("Silent Engrams", str(role.memory.silent_engrams))
    table.add_row("Tools", ", ".join(role.tools) or "none")

    console.print(table)
    console.print("[green]✅ Configuration valid[/green]")


def _run_interactive_agent_loop(agent) -> None:
    """Run the interactive loop for an agent."""
    console.print(f"[bold cyan]🧠 Agent '{agent.name}' active (model={agent.model})[/bold cyan]")
    console.print(
        f"[dim]Budget: {agent.guardrail.max_tokens} tokens | "
        f"L1: {agent.working_memory.max_tokens} tokens[/dim]"
    )
    console.print("[dim]Type 'exit' or Ctrl+C to quit.[/dim]\n")

    try:
        while True:
            try:
                user_input = console.input("[bold green]> [/bold green]")
            except EOFError:
                break

            if user_input.strip().lower() in ("exit", "quit", "q"):
                break

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = max(1, len(user_input) // 4)

            if not agent.guardrail.consume(estimated_tokens):
                console.print("[red]⛔ Session budget exhausted. Agent terminated.[/red]")
                break

            agent.guardrail.tick_turn()

            # Echo status (placeholder for actual LLM call)
            console.print(
                f"[dim](tokens: {agent.guardrail.consumed}/"
                f"{agent.guardrail.max_tokens}, "
                f"turn: {agent.guardrail.turns})[/dim]"
            )
            console.print(f"[yellow]🤖 [{agent.model}] Processing: {user_input[:80]}...[/yellow]\n")

    except KeyboardInterrupt:
        console.print("\n[dim]Agent session ended.[/dim]")

    # Final status
    console.print_json(json.dumps(agent.guardrail.status(), indent=2))


@agent_cmds.command("run")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to role.yaml.",
)
@click.option("--dry-run", is_flag=True, help="Compile but don't execute.")
def agent_run(config: str, dry_run: bool):
    """Compile and run an agent from a YAML role definition."""
    from cortex.agent.loader import load_agent

    try:
        agent = load_agent(config)
    except Exception as e:
        console.print(f"[red]❌ Failed to compile agent: {e}[/red]")
        sys.exit(1)

    if dry_run:
        console.print(f"[green]✅ Agent '{agent.name}' compiled successfully (dry-run)[/green]")
        console.print_json(json.dumps(agent.status(), indent=2))
        return

    _run_interactive_agent_loop(agent)
