"""CLI commands for the E2E Pipeline — `cortex run` and `cortex pipeline`.

Provides the primary E2E entry point for executing intents through
the full CORTEX pipeline: Ingress → Context → Plan → Execute → Persist → Egress.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from typing import Any

import click

from cortex.cli.common import cli


@cli.command("run")
@click.argument("intent", nargs=-1, required=True)
@click.option("--budget", "-b", default=0.10, type=float, help="Max budget in USD (default: $0.10)")
@click.option(
    "--output",
    "-o",
    default="stdout",
    type=click.Choice(["stdout", "file", "json", "memory"]),
    help="Delivery target",
)
@click.option(
    "--file", "-f", "output_file", default=None, help="Output file path (when --output=file)"
)
@click.option(
    "--hints", "-h", "context_hints", multiple=True, help="KI names for context pre-fetch"
)
@click.option("--timeout", "-t", default=120.0, type=float, help="Timeout in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Show stage-by-stage telemetry")
def run_pipeline(
    intent: tuple[str, ...],
    budget: float,
    output: str,
    output_file: str | None,
    context_hints: tuple[str, ...],
    timeout: float,
    verbose: bool,
) -> None:
    """Execute an intent through the full E2E CORTEX pipeline.

    \b
    Examples:
        cortex run "analyze security patterns in this codebase"
        cortex run "research state of the art in formal verification" --budget 0.05
        cortex run "find vulnerability" --hints exactly_protocol_strikes_2026
        cortex run "summarize my KIs" --output file -f /tmp/summary.md
    """
    from cortex.pipeline import DeliveryTarget, DeliveryType, PipelineRequest

    intent_str = " ".join(intent)

    # Map CLI output option to DeliveryType
    delivery_map = {
        "stdout": DeliveryType.STDOUT,
        "file": DeliveryType.FILE,
        "json": DeliveryType.STDOUT,
        "memory": DeliveryType.MEMORY,
    }
    delivery_type = delivery_map.get(output, DeliveryType.STDOUT)
    fmt = "json" if output == "json" else "markdown"

    target = DeliveryTarget(
        type=delivery_type,
        path=output_file,
        format=fmt,
    )

    request = PipelineRequest(
        intent=intent_str,
        context_hints=list(context_hints),
        budget_limit_usd=budget,
        delivery=target,
        timeout_s=timeout,
    )

    # Execute
    result = asyncio.run(_execute_pipeline(request, verbose))

    # Exit code based on status
    if result.status.value != "success":
        sys.exit(1)


async def _execute_pipeline(request: Any, verbose: bool) -> Any:
    """Async pipeline execution wrapper."""
    from cortex.pipeline.bridge import CortexPipelineBridge

    start = time.time()
    bridge = CortexPipelineBridge()

    try:
        await bridge.initialize()
        result = await bridge.run(request)

        if verbose:
            _print_telemetry(result)

        _print_summary(result, time.time() - start)
        return result

    finally:
        await bridge.close()


def _print_telemetry(result: Any) -> None:
    """Print stage-by-stage telemetry."""
    click.echo("\n┌─── Pipeline Telemetry ───────────────────────┐")
    for stage in result.stages:
        status = "✓" if not stage.error else f"✗ {stage.error}"
        click.echo(f"│ {stage.stage.value:<12} │ {stage.latency_ms:>7.1f}ms │ {status}")
    click.echo("└──────────────────────────────────────────────┘")


def _print_summary(result: Any, wall_time: float) -> None:
    """Print pipeline execution summary."""
    status_icons = {
        "success": "✅",
        "failed": "❌",
        "budget_exhausted": "🛑",
        "cancelled": "⚠️",
    }
    icon = status_icons.get(result.status.value, "❓")

    click.echo(f"\n{icon} Pipeline {result.status.value.upper()}")
    click.echo(f"   Mission:  {result.mission_id}")
    click.echo(f"   Latency:  {result.latency_ms:.0f}ms")
    click.echo(f"   Cost:     ${result.cost_usd:.4f}")
    click.echo(f"   Agents:   {', '.join(result.agent_chain) if result.agent_chain else 'none'}")
    click.echo(f"   Context:  {len(result.context_used)} sources")
    click.echo(
        f"   Ledger:   {result.ledger_hash[:16]}..."
        if result.ledger_hash
        else "   Ledger:   (none)"
    )

    if result.error:
        click.echo(f"   Error:    {result.error}")


@cli.group("pipeline")
def pipeline_group() -> None:
    """Pipeline management commands."""


@pipeline_group.command("status")
def pipeline_status() -> None:
    """Show pipeline configuration and health."""
    import os

    click.echo("═══ CORTEX E2E Pipeline Status ═══\n")

    # Check ChromaDB
    chroma_path = os.path.expanduser("~/.cortex/chroma_db")
    chroma_ok = os.path.exists(chroma_path)
    click.echo(f"  ChromaDB:        {'✅ ' + chroma_path if chroma_ok else '❌ not initialized'}")

    # Check Budget DB
    budget_path = os.path.expanduser("~/.cortex/budget.db")
    budget_ok = os.path.exists(budget_path)
    click.echo(f"  Budget Manager:  {'✅ ' + budget_path if budget_ok else '❌ not initialized'}")

    # Check Pipeline Ledger
    ledger_path = os.path.expanduser("~/.cortex/pipeline_ledger.jsonl")
    ledger_ok = os.path.exists(ledger_path)
    if ledger_ok:
        with open(ledger_path) as f:
            lines = sum(1 for _ in f)
        click.echo(f"  Pipeline Ledger: ✅ {lines} entries")
    else:
        click.echo("  Pipeline Ledger: ❌ no entries yet")

    # Check Engine DB
    from cortex.config import DEFAULT_DB_PATH

    engine_ok = os.path.exists(os.path.expanduser(str(DEFAULT_DB_PATH)))
    click.echo(f"  Engine DB:       {'✅' if engine_ok else '❌'} {DEFAULT_DB_PATH}")

    # Router capabilities
    from cortex.router.router import AgentRouter

    router = AgentRouter()
    click.echo(f"\n  Router Agents:   {len(router._caps)}")
    for cap in router._caps:
        click.echo(f"    • {cap.agent_id} (priority={cap.priority}, provider={cap.provider})")


@pipeline_group.command("history")
@click.option("--limit", "-n", default=10, help="Number of entries to show")
def pipeline_history(limit: int) -> None:
    """Show recent pipeline execution history from the ledger."""
    import os

    ledger_path = os.path.expanduser("~/.cortex/pipeline_ledger.jsonl")
    if not os.path.exists(ledger_path):
        click.echo("No pipeline history yet.")
        return

    with open(ledger_path) as f:
        lines = f.readlines()

    recent = lines[-limit:]
    click.echo(f"═══ Last {min(limit, len(recent))} Pipeline Runs ═══\n")
    for line in reversed(recent):
        try:
            entry = json.loads(line.strip())
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("timestamp", 0)))
            click.echo(
                f"  {ts}  {entry.get('mission_id', '?'):<16}  "
                f"hash={entry.get('result_hash', '?')[:12]}..."
            )
        except json.JSONDecodeError:
            continue
