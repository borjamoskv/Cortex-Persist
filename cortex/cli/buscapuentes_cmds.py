"""CORTEX CLI — Buscapuentes (Sovereign Bridge Locator).

Finds C5-Dynamic bridges and high-exergy transactions in the Master Ledger.
"""

import json
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cortex.cli.common import DEFAULT_DB, _run_async, cli, get_engine, cortex_theme

console = Console(theme=cortex_theme)

@cli.command("buscapuentes")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--limit", default=50, help="Max bridges to show")
@click.option("--project", default="", help="Filter by project")
@click.option("--brutal", is_flag=True, help="Show raw JSON detail for each bridge")
def buscapuentes_cmd(db: str, limit: int, project: str, brutal: bool) -> None:
    """Scan the CORTEX Ledger for crystallized C5-Dynamic bridges."""
    
    async def _run():
        engine = get_engine(db)
        try:
            await engine.init_db()
            ledger_inst = engine.ledger
            
            if not ledger_inst:
                console.print("[bold red]🚨 Ledger not available in engine.[/]")
                return

            # Directly query the transactions table for bridge patterns
            query = """
                SELECT id, project, action, detail, hash, timestamp 
                FROM transactions 
                WHERE (
                    action LIKE '%bridge%' 
                    OR detail LIKE '%C5-Dynamic%' 
                    OR detail LIKE '%exergy%'
                    OR action LIKE '%crystallize%'
                )
            """
            params: list[str | int] = []
            
            if project:
                query += " AND project = ?"
                params.append(project)
                
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            async with ledger_inst._acquire_conn() as conn:
                cursor = await conn.execute(query, tuple(params))
                rows = await cursor.fetchall()

            if not rows:
                console.print(Panel("[yellow]No C5-Dynamic bridges found in the Ledger.[/]", title="Buscapuentes"))
                return

            console.print(f"\n[bold blue]🌉 CORTEX Buscapuentes[/bold blue] (Found [cyan]{len(rows)}[/cyan] bridges)")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Project", style="green", width=20)
            table.add_column("Action", style="cyan", width=25)
            table.add_column("Exergy/Confidence", style="yellow")
            if brutal:
                table.add_column("Hash", style="dim", width=12)

            for row in rows:
                tid, proj, act, det_str, hsh, ts = row
                try:
                    det = json.loads(det_str)
                    # Extract interesting metrics if available
                    exergy = det.get("delta", det.get("exergy", det.get("exergy_estimate", "")))
                    conf = det.get("confidence", "")
                    
                    info = []
                    if exergy: info.append(f"ΔE: {exergy}")
                    if conf: info.append(f"C: {conf}")
                    
                    info_str = " | ".join(info)
                    
                    if brutal:
                        # If brutal, we just dump the JSON
                        info_str = det_str[:100] + "..." if len(det_str) > 100 else det_str
                except Exception:
                    info_str = det_str[:50]
                
                short_hash = hsh[:8] + "..."

                row_data = [str(tid), proj, act, info_str]
                if brutal:
                    row_data.append(short_hash)
                    
                table.add_row(*row_data)

            console.print(table)

        finally:
            await engine.close()

    _run_async(_run())
