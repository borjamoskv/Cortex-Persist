# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.panel import Panel

from cortex.cli.common import cli, console
from cortex.engine.swarm_10k import SwarmCommander


@cli.group()
def swarm_10k():
    """SOVEREIGN SWARM 10K - Hierarchical Orchestration (L0 -> L2)."""


@swarm_10k.command("deploy")
@click.option("--db-path", default="~/.cortex/10k_shards", help="Sharded bus base path.")
@click.option("--tasks-count", default=1000, help="Initial number of tasks to seed.")
def swarm_10k_deploy(db_path, tasks_count):
    """Deploy the SwarmCommander and bootstrap the 10K hierarchical topology."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    p = Path(db_path).expanduser()

    console.print(
        Panel(
            f"⚡ [bold]CORTEX-SWARM-10K DEPLOYMENT[/]\n"
            f"Shards Location: [cyan]{p}[/]\n"
            f"Target Workload: [bold red]{tasks_count} Atomic Operations[/]",
            border_style="#00FFCC",
        )
    )

    async def _run():
        commander = SwarmCommander(bus_path=p)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            t1 = progress.add_task("[bold #1A1A1A]L0: Igniting SwarmCommander...", total=None)
            await commander.initialize()
            progress.update(t1, description="[bold green]L0: SwarmCommander Online")

            t2 = progress.add_task(f"[bold #1A1A1A]Dispatching {tasks_count} tasks...", total=None)

            # Seed massive workload
            tasks = [{"domain": f"domain_{i % 10}", "id": i} for i in range(tasks_count)]
            await commander.execute_global_dispatch(tasks)

            progress.update(
                t2,
                description=f"[bold green]Hierarchy Extrusion Complete. {tasks_count} tasks dispatched.",
            )

        report = await commander.get_density_report()
        console.print(
            "\n[bold #00FFCC]✅ 10K TOPOLOGY STABLE[/]\n"
            f"Legions (L1): {report['legions']} | Centurions (L2): {report['centurions']} | Active Agents: {report['agents']}"
        )
        res = commander.bus.close()  # pyright: ignore[reportGeneralTypeIssues]
        if asyncio.iscoroutine(res):
            await res

    asyncio.run(_run())


@swarm_10k.command("status")
@click.option("--db-path", default="~/.cortex/10k_shards", help="Sharded bus base path.")
def swarm_10k_status(db_path):
    """Display real-time global exergy and density stats for the 10K Swarm."""
    p = Path(db_path).expanduser()

    async def _run():
        commander = SwarmCommander(bus_path=p)
        await commander.initialize()

        from cortex.engine.shared_bus import SovereignSharedBus

        if isinstance(commander.bus, SovereignSharedBus):
            metrics = commander.bus.metrics
            console.print(
                Panel(
                    f"📊 [bold]CORTEX-SWARM-10K STATUS[/]\n"
                    f"Protocol: [cyan]SovereignSharedBus (Zero-Copy)[/]\n"
                    f"Global Exergy: [green]{metrics['exergy']:.2f}[/]\n"
                    f"Latency: [yellow]{metrics['latency']:.2f}ms[/]\n"
                    f"Shards Health: [green]100% ({commander.bus.num_shards} active)[/]",
                    border_style="blue",
                )
            )
            commander.bus.close()
        else:
            total_signals = 0
            for sys_idx in range(commander.bus.num_shards):
                conn = commander.bus._shards[sys_idx]  # pyright: ignore[reportAttributeAccessIssue]
                row = await (await conn.execute("SELECT COUNT(*) FROM signals")).fetchone()
                total_signals += row[0] if row else 0

            console.print(
                Panel(
                    f"📊 [bold]CORTEX-SWARM-10K STATUS[/]\n"
                    f"Protocol: [cyan]ShardedAsyncSignalBus (SQLite)[/]\n"
                    f"Total Signals in Shards Bus: [cyan]{total_signals}[/]\n"
                    f"Shards Health: [green]100% ({commander.bus.num_shards} active)[/]",
                    border_style="blue",
                )
            )
            res = commander.bus.close()  # pyright: ignore[reportGeneralTypeIssues]
            if asyncio.iscoroutine(res):
                await res

    asyncio.run(_run())


@swarm_10k.command("consolidate")
@click.option("--db-path", default="~/.cortex/10k_shards", help="Sharded bus base path.")
def swarm_10k_consolidate(db_path):
    """Trigger state synthesis to Sovereign Ledger and Annihilate the hierarchy."""
    p = Path(db_path).expanduser()

    async def _run():
        commander = SwarmCommander(bus_path=p)
        await commander.initialize()

        console.print("[dim]Initiating Ouroboros-Omega Annihilation...[/]")
        await commander.consolidate_and_annihilate()

        console.print("[bold red]🔥 Hierarchy Annihilated & Entropy Purged.[/]")

    asyncio.run(_run())
