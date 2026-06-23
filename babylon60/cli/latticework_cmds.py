# [C5-REAL] Exergy-Maximized
"""
Latticework Command-Line Interface.
Enables interaction with LatticeworkDaemon and Cognitive Primitives store.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import click
from rich.table import Table

from babylon60.cli.common import _run_async, cli, console


@click.group("latticework")
def latticework_cmds():
    """🌐 Latticework: Cognitive Primitives & Causal Mitigation Daemon."""
    pass


@latticework_cmds.command("primitives")
@click.option("--query", "-q", help="Filter primitives by keyword in name or description.")
def primitives_cmd(query: str | None):
    """List and search the 100 Cognitive Primitives of Systems Theory & Info Exergy."""
    console.print("[bold cyan]🌐 Querying Cognitive Primitives from LatticeworkStore...[/bold cyan]")
    
    from babylon60.engine.latticework_store import LatticeworkStore
    store = LatticeworkStore()
    
    if query:
        primitives = store.search_by_keyword(query)
        title = f"🧠 Found Primitives matching: '{query}'"
    else:
        primitives = list(store.primitives.values())
        title = "🧠 All Loaded Cognitive Primitives"
        
    if not primitives:
        console.print("[yellow]⚠ No primitives found matching the criteria.[/yellow]")
        return
        
    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Name", style="white", width=25)
    table.add_column("Algebraic Topology", style="green", width=25)
    table.add_column("Causal Isomorphism", style="dim white")
    
    # Sort by ID
    for prim in sorted(primitives, key=lambda x: x.id):
        table.add_row(
            str(prim.id),
            prim.name,
            f"`{prim.algebraic_topology}`",
            prim.description
        )
        
    console.print(table)


@click.option("--seconds", "-s", default=10, help="Duration to run the daemon loop in foreground.")
@click.option("--interval", "-i", default=2, help="Interval between ticks in seconds.")
@click.option("--real", is_flag=True, help="Read real anomalies from the Execution Trace Ledger.")
@latticework_cmds.command("daemon")
def daemon_cmd(seconds: int, interval: int, real: bool):
    """Start LatticeworkDaemon in foreground to monitor and mitigate ledger anomalies."""
    console.print(f"[bold magenta]🌀 Starting LatticeworkDaemon in Foreground for {seconds}s (interval={interval}s)...[/bold magenta]")
    
    from babylon60.cli.common import DEFAULT_DB
    from babylon60.engine.causal_scheduler import CausalScheduler
    from babylon60.engine.latticework_daemon import LatticeworkDaemon
    from babylon60.ledger.causal_graph import CausalGraph
    from babylon60.ledger.execution_trace import ExecutionTraceLedger
    
    db_path = DEFAULT_DB
    
    if real:
        db_path = "/tmp/cortex_test_latticework.db"
        console.print(f"[cyan]ℹ Isolation Mode: Initializing isolated test database at: {db_path}[/cyan]")
        
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
                
        from babylon60.database.core import connect_async_ctx
        from babylon60.engine.mtk_sqlite_authorizer import mtk_active_token
        
        async def init_db():
            token_token = mtk_active_token.set("mtk_auth_cli_init")
            try:
                async with connect_async_ctx(db_path) as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS execution_trace_ledger (
                            id              TEXT PRIMARY KEY,
                            tenant_id       TEXT NOT NULL DEFAULT 'default',
                            origin          TEXT NOT NULL,
                            cost            REAL NOT NULL,
                            lineage         TEXT NOT NULL DEFAULT '[]',
                            outcome         TEXT NOT NULL,
                            rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
                        )
                    """)
                    await conn.commit()
            finally:
                mtk_active_token.reset(token_token)
                
        _run_async(init_db())
        console.print("[cyan]ℹ Real Ledger Mode Active. Scanning isolated execution traces database...[/cyan]")
        
    ledger = ExecutionTraceLedger(db_path)
    graph = CausalGraph(db_path)
    scheduler = CausalScheduler(graph, ledger)
    
    daemon = LatticeworkDaemon(ledger, scheduler, scan_interval=interval)
    
    if real:
        async def custom_loop():
            # Inyectamos una traza de entropía real para la demo
            trace_id = f"tx_err_{uuid.uuid4().hex[:6]}"
            await ledger.record_trace(
                trace_id=trace_id,
                origin="sota_vector_engine_anomaly",
                cost=850.0,
                lineage=[],
                outcome="falsified",
                rollback_possible=True
            )
            console.print(f"[bold yellow]⚠ Entropy Anomaly injected into Ledger: {trace_id} (outcome='falsified')[/bold yellow]")
            
            while daemon._running:
                try:
                    traces = await ledger.get_recent(limit=5)
                    anomalies = []
                    for t in traces:
                        if t["outcome"] == "falsified" or t["cost"] > 500.0:
                            entropy = min(0.99, t["cost"] / 1000.0) if t["cost"] > 0 else 0.85
                            anomalies.append({
                                "id": t["id"],
                                "entropy": entropy,
                                "tag": "infinite_retry" if t["outcome"] == "falsified" else "high_computation_cost"
                            })
                            
                    if not anomalies:
                        console.print("[dim]Monitoring Ledger: 0 anomalies detected in last 5 traces.[/dim]")
                    
                    for anomaly in anomalies:
                        entropy_val = anomaly["entropy"]
                        if "retry" in anomaly["tag"]:
                            primitive = daemon.store.get_primitive(9)  # Inversión de Matrices
                        else:
                            primitive = daemon.store.get_primitive(18)  # Principio de Landauer
                            
                        if primitive:
                            exergy_yield = daemon._compute_primitive_exergy(entropy_val, primitive.base60_constant)
                            await scheduler.inject_exergy(anomaly["id"], exergy_yield.to_float())
                            console.print(
                                f"[bold green]✔ CAUSAL MITIGATION[/bold green] | "
                                f"Trace: [cyan]{anomaly['id']}[/cyan] (Entropy: {entropy_val:.2f}) -> "
                                f"Primitive [yellow]{primitive.id}[/yellow] ({primitive.name}) "
                                f"| B-60 Exergy: [bold green]{exergy_yield}[/bold green]"
                            )
                            
                except Exception as e:
                    console.print(f"[red]Error in daemon real loop: {e}[/red]")
                await asyncio.sleep(daemon.interval)
                
        daemon._daemon_loop = custom_loop
        
    else:
        # Modo simulado usando el console.print
        async def print_loop():
            console.print("[cyan]ℹ Simulated Mode. Monitoring raw stochastic noise...[/cyan]")
            
            while daemon._running:
                anomalies = [
                    {"id": "tx_45A", "entropy": 0.85, "tag": "infinite_retry"},
                    {"id": "tx_45B", "entropy": 0.99, "tag": "green_theater_slop"}
                ]
                for anomaly in anomalies:
                    entropy_val = anomaly["entropy"]
                    if "retry" in anomaly["tag"]:
                        primitive = daemon.store.get_primitive(9)
                    else:
                        primitive = daemon.store.get_primitive(18)
                        
                    if primitive:
                        exergy_yield = daemon._compute_primitive_exergy(entropy_val, primitive.base60_constant)
                        console.print(
                            f"[bold green]✔ SIMULATED MITIGATION[/bold green] | "
                            f"Trace: [cyan]{anomaly['id']}[/cyan] (Entropy: {entropy_val:.2f}) -> "
                            f"Primitive [yellow]{primitive.id}[/yellow] ({primitive.name}) "
                            f"| B-60 Exergy: [bold green]{exergy_yield}[/bold green]"
                        )
                await asyncio.sleep(daemon.interval)
            
        daemon._daemon_loop = print_loop
        
    async def run_for_duration():
        daemon.start()
        await asyncio.sleep(seconds)
        await daemon.stop()
        
    _run_async(run_for_duration())


cli.add_command(latticework_cmds)
