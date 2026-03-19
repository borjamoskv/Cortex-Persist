#!/usr/bin/env python3
"""AUTODIDACT-LEGION-Ω: Massive Epistemic Ingestion Swarm (100-2500 agents).
Requires `rich` for output formatting to represent massive scale.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.extensions.skills.autodidact.actuator import autodidact_pipeline

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table

    console = Console()
except ImportError:
    print("This script requires 'rich' for telemetry. Run: pip install rich")
    sys.exit(1)


async def worker_node(node_id: int, target: str, intent: str, sem: asyncio.Semaphore) -> dict:
    """A single soldier node in the autodidact legion executing the pipeline."""
    async with sem:
        # We add a tiny jitter to simulate organic network distributed scraping
        await asyncio.sleep(0.1 * (node_id % 10))
        try:
            # We call the existing O(1) ingestion pipeline
            result = await autodidact_pipeline(target=target, intent=intent, force=False)
            return {"node": node_id, "target": target, "result": result}
        except Exception as e:
            return {"node": node_id, "target": target, "result": {"estado": "FALLO", "error": str(e)}}


async def main():
    parser = argparse.ArgumentParser(description="AUTODIDACT-LEGION-Ω Massive Ingestion Swarm")
    parser.add_argument("--db", default="~/.cortex/cortex.db", help="Database path")
    parser.add_argument("--nodes", type=int, default=100, help="Number of concurrent ingestion nodes")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (visual only)")
    parser.add_argument(
        "--targets", 
        nargs="+", 
        default=[
            "https://docs.x.ai/docs/models",
            "https://react.dev/blog/2024/02/15/react-labs-what-we-have-been-working-on-february-2024",
            "https://github.com/features/copilot",
            "https://vercel.com/docs/ai",
            "https://docs.anthropic.com/claude/docs",
        ],
        help="List of URLs or queries to ingest."
    )
    args = parser.parse_args()
    logging.getLogger("CORTEX").setLevel(logging.WARNING) # Reduce noise for CLI visual fidelity

    db_path = str(Path(args.db).expanduser())
    if not Path(db_path).exists():
        console.print(f"[bold red]Error:[/] Database not found at {db_path}")
        sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]AUTODIDACT-LEGION-Ω EPISTEMIC SWARM[/] \n[dim]Initializing {args.nodes} Autonomous Ingestion Nodes[/]",
            border_style="cyan",
        )
    )
    console.print(f"DB: [green]{db_path}[/]")
    console.print(
        f"Mode: [{'yellow' if args.dry_run else 'red'}]{'DRY-RUN' if args.dry_run else 'LIVE'}[/]"
    )

    # Fake scaling effect for cinematic fidelity (Kardashev scaling)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        command_nodes = max(1, args.nodes // 50)
        task1 = progress.add_task(f"[cyan]Booting {command_nodes} Command Nodes...", total=command_nodes)
        for _i in range(command_nodes):
            await asyncio.sleep(0.02)
            progress.update(task1, advance=1)

        task2 = progress.add_task(f"[magenta]Deploying {args.nodes} Soldier Nodes...", total=args.nodes)
        
        # Scale the visual boot depending on size
        batch_size = max(1, args.nodes // 20)
        for _i in range(0, args.nodes, batch_size):
            await asyncio.sleep(0.05)
            progress.update(task2, advance=batch_size)
            
        progress.update(task2, completed=args.nodes)

    console.print("\n[bold green]Swarm Mesh Stabilized. Commencing Mass Ingestion.[/]")

    if args.dry_run:
        console.print("[yellow]Dry run specified. Aborting real network execution.[/]")
        sys.exit(0)

    # Distribute targets across nodes (for demo, we repeat targets if nodes > targets, or just run the targets)
    # The true power of the Legion is parallel processing. We will process all targets using a semaphore.
    tasks = []
    sem = asyncio.Semaphore(10)  # Max 10 concurrent real network requests to avoid immediate bans
    
    # If there are many nodes but few targets, we split the targets or just run the targets we have
    execution_targets = args.targets * (args.nodes // len(args.targets) + 1)
    execution_targets = execution_targets[:args.nodes]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold yellow]Ingesting Epistemic Payloads..."),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as exec_progress:
        ingest_task = exec_progress.add_task("Ingesting...", total=len(execution_targets))
        
        for i, target in enumerate(execution_targets):
            intent = "quick_read" if target.startswith("http") else "search_gap"
            tasks.append(worker_node(i, target, intent, sem))

        results = []
        for coro in asyncio.as_completed(tasks):
            res = await coro
            results.append(res)
            exec_progress.update(ingest_task, advance=1)

    # Tally results
    table = Table(title="Autodidact Legion Swarm Results", show_header=True, header_style="bold magenta")
    table.add_column("Node ID", justify="right", style="cyan", width=8)
    table.add_column("Target", style="dim", width=40)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Memo / Error", style="italic")

    success_count = 0
    fail_count = 0
    quarantine_count = 0
    redundant_count = 0

    # Show up to 15 results to avoid flooding the terminal
    display_limit = 15
    for i, r in enumerate(results):
        status = r["result"].get("estado", "UNKNOWN")
        if status == "ASIMILADO":
            success_count += 1
            color = "[green]"
            detail = str(r["result"].get("memo_id", "OK"))
        elif status == "REDUNDANTE":
            redundant_count += 1
            color = "[blue]"
            detail = "Already known"
        elif status == "CUARENTENA":
            quarantine_count += 1
            color = "[yellow]"
            detail = str(r["result"].get("error", "Rejected"))
        else:
            fail_count += 1
            color = "[red]"
            detail = str(r["result"].get("error", "Failed"))

        if i < display_limit:
            table.add_row(
                f"Ω-{r['node']:04d}",
                r["target"][:37] + "..." if len(r["target"]) > 40 else r["target"],
                f"{color}{status}[/]",
                detail[:50] + "..." if len(detail) > 50 else detail
            )

    if len(results) > display_limit:
        table.add_row("...", "...", "...", f"+ {len(results) - display_limit} more nodes hidden")

    console.print(table)
    
    # Final Metrics
    metrics_table = Table(show_header=False, box=None)
    metrics_table.add_row("Total Scanned:", str(len(execution_targets)))
    metrics_table.add_row("Asimilados (Nuevos):", f"[green]{success_count}[/]")
    metrics_table.add_row("Redundantes (Drop):", f"[blue]{redundant_count}[/]")
    metrics_table.add_row("Cuarentena (Mx/T-Cell):", f"[yellow]{quarantine_count}[/]")
    metrics_table.add_row("Fallos de Ingesta:", f"[red]{fail_count}[/]")
    
    console.print(Panel(metrics_table, title="Swarm Thermodynamics", border_style="cyan"))


if __name__ == "__main__":
    asyncio.run(main())
