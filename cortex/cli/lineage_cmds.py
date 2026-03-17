"""CORTEX CLI — Lineage & Epistemic Audit Commands.

Provides verification of Ω₃-V: Verifiable Lineage.
"""

from __future__ import annotations

import asyncio
import re

import click
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from cortex.cli.common import DEFAULT_DB, cli
from cortex.core.lineage import LineageNode, LineageVerifier
from cortex.engine import CortexEngine

console = Console()


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@cli.group("lineage")
def lineage_group():
    """Epistemic lineage (Ω₃-V) commands."""
    pass


@lineage_group.command("trace")
@click.argument("fact_id", type=int)
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--depth", default=5, help="Max recursion depth")
def trace_lineage(fact_id: int, db: str, depth: int):
    """Trace the heredity tree of a fact back to L0 sources."""

    async def _trace():
        engine = CortexEngine(db)
        verifier = LineageVerifier(engine)
        root = await verifier.get_lineage(fact_id, max_depth=depth)

        def build_rich_tree(node: LineageNode, tree_obj: Tree | None = None) -> Tree:
            status = "[green]✅[/green]" if node.is_valid else "[red]❌[/red]"
            text = f"{status} [bold]#{node.fact_id}[/bold] [{node.fact_type}] "
            label = f"{text}{node.content[:60]}..."
            if tree_obj is None:
                tree_obj = Tree(label)
            else:
                tree_obj = tree_obj.add(label)

            for p in node.parents:
                build_rich_tree(p, tree_obj)
            return tree_obj

        rich_tree = build_rich_tree(root)
        console.print(Panel(rich_tree, title=f"Trace: Fact #{fact_id}", border_style="cyan"))

        if not root.is_valid:
            console.print(f"\n[bold red]Ω₃-V VIOLATION:[/bold red] {root.error or 'Broken'}")
        else:
            console.print("\n[bold green]Ω₃-V VERIFIED:[/bold green] grounded.")

    _run_async(_trace())


@cli.command("audit-file")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--db", default=DEFAULT_DB, help="Database path")
def audit_file(file_path: str, db: str):
    """Scan a file for fact IDs and verify their epistemic lineage."""
    with open(file_path) as f:
        content = f.read()

    # Simple regex to find mentions like #123 or Fact #123
    fact_ids = [int(fid) for fid in re.findall(r"(?:Fact\s+)?#(\d+)", content)]
    fact_ids = list(set(fact_ids))  # unique

    if not fact_ids:
        console.print("[yellow]No fact IDs found in file.[/yellow]")
        return

    console.print(f"Auditing {len(fact_ids)} facts found in [bold]{file_path}[/bold]...\n")

    async def _audit_all():
        engine = CortexEngine(db)
        verifier = LineageVerifier(engine)

        valid_count = 0
        for fid in fact_ids:
            node = await verifier.get_lineage(fid, max_depth=1)
            status = "[green]VALID[/green]" if node.is_valid else "[red]BROKEN[/red]"
            console.print(f"Fact #{fid}: {status} - {node.content[:50]}...")
            if node.is_valid:
                valid_count += 1

        console.print(f"\n[bold]Audit Result:[/bold] {valid_count}/{len(fact_ids)} verified.")
        if valid_count < len(fact_ids):
            console.print(
                "[bold red]WARNING:[/bold red] Some insights in this file are not grounded!"
            )

    _run_async(_audit_all())
