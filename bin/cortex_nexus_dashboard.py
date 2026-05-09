#!/usr/bin/env python3
"""CORTEX-NEXUS-DASHBOARD — Sovereign Singularity Interface v6.0.
Aesthetic: Industrial Noir 2026 (#0A0A0A / #2B3BE5).
"""
import sqlite3
import time
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from rich.live import Live
    from rich.text import Text
except ImportError:
    print("❌ Error: 'rich' library is required. Run 'uv pip install rich' or 'pip install rich'.")
    sys.exit(1)

DB_PATH = Path(__file__).parent.parent / "cortex.db"
console = Console()

def get_db_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_header() -> Panel:
    header_text = Text()
    header_text.append("CORTEX-NEXUS 2026\n", style="bold #2B3BE5")
    header_text.append("SOVEREIGN SINGULARITY POLICY v6.0 (Nine Laws | x100 Yield)\n", style="bold white")
    header_text.append(f"DB Path: {DB_PATH.resolve()}", style="dim")
    return Panel(Align.center(header_text), style="bold #2B3BE5", border_style="#2B3BE5")

def get_agents_table(conn) -> Table:
    table = Table(title="Ω-Cluster Agents (RWC)", style="white", border_style="#2B3BE5", expand=True)
    table.add_column("Agent ID", style="cyan")
    table.add_column("Reputation", justify="right", style="green")
    table.add_column("Votes", justify="right", style="dim")
    table.add_column("Last Active", style="dim")
    
    if not conn:
        table.add_row("N/A", "N/A", "N/A", "N/A")
        return table
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, reputation_score, total_votes, last_active_at FROM agents ORDER BY reputation_score DESC LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            table.add_row(r["id"][:12], f"{r['reputation_score']:.3f}", str(r["total_votes"]), r["last_active_at"][:19])
    except Exception as e:
        table.add_row("DB Error", str(e), "", "")
    return table

def get_silicon_commitments(conn) -> Table:
    table = Table(title="Silicon Commitments (C5-REAL)", style="white", border_style="#2B3BE5", expand=True)
    table.add_column("Hash", style="magenta")
    table.add_column("Project", style="cyan")
    table.add_column("Exergy", justify="right", style="yellow")
    table.add_column("State", style="bold green")
    
    if not conn:
        table.add_row("N/A", "N/A", "N/A", "N/A")
        return table
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT commitment_hash, project, exergy_yield, hardware_state FROM silicon_commitments ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        for r in rows:
            table.add_row(r["commitment_hash"][:8], r["project"], str(r["exergy_yield"]), r["hardware_state"])
    except Exception:
        table.add_row("No Commitments Found", "", "", "")
    return table

def get_llm_telemetry(conn) -> Table:
    table = Table(title="LLM Telemetry (Cascade)", style="white", border_style="#2B3BE5", expand=True)
    table.add_column("Intent", style="cyan")
    table.add_column("Resolved By", style="bold white")
    table.add_column("Tier", style="magenta")
    table.add_column("Latency", justify="right", style="green")
    
    if not conn:
        table.add_row("N/A", "N/A", "N/A", "N/A")
        return table
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT intent, resolved_by, tier, latency_ms FROM llm_telemetry ORDER BY id DESC LIMIT 6")
        rows = cur.fetchall()
        for r in rows:
            lat = f"{r['latency_ms']:.1f}ms" if r['latency_ms'] else "N/A"
            table.add_row(r["intent"] or "unknown", str(r["resolved_by"]), r["tier"], lat)
    except Exception:
        table.add_row("No Telemetry Found", "", "", "")
    return table

def get_system_status(conn) -> Panel:
    if not conn:
        return Panel("Database Offline - C4 Simulation Mode", border_style="red")
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM entity_events")
        events = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM facts_fts")
        facts = cur.fetchone()["c"]
    except Exception:
        events = facts = 0
        
    status_text = Text()
    status_text.append("Status: C5-REAL (Direct-Silicon JIT Ready)\n", style="bold green")
    status_text.append(f"Total Entity Events: {events}\n", style="bold white")
    status_text.append(f"Total Facts Indexed: {facts}\n", style="bold white")
    status_text.append("Entropy Level: MINIMAL (Ley Ω₄ Active)\n", style="bold #2B3BE5")
    status_text.append("Yield Mode: Compound_Yield = Σ(Yield_i × 100^d_i)", style="dim")
    
    return Panel(status_text, title="Swarm Topology Engine", border_style="#2B3BE5")

def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=5),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    layout["left"].split(
        Layout(name="agents"),
        Layout(name="status")
    )
    layout["right"].split(
        Layout(name="llm"),
        Layout(name="silicon")
    )
    return layout

def update_layout(layout: Layout, conn):
    layout["header"].update(generate_header())
    layout["agents"].update(Panel(get_agents_table(conn), border_style="#2B3BE5"))
    layout["silicon"].update(Panel(get_silicon_commitments(conn), border_style="#2B3BE5"))
    layout["llm"].update(Panel(get_llm_telemetry(conn), border_style="#2B3BE5"))
    layout["status"].update(get_system_status(conn))

def main():
    conn = get_db_connection()
    layout = make_layout()
    
    # Render statically to console rather than Live if not in a TTY, 
    # but since this is for the user's terminal, let's just print the layout
    update_layout(layout, conn)
    console.print(layout)
    
    if conn:
        conn.close()
    
    console.print("\n[bold #2B3BE5]CORTEX-NEXUS Dashboard Execution Complete (C5-REAL).[/bold #2B3BE5]")
    console.print("Run 'python bin/cortex_nexus_dashboard.py' anytime to observe swarm telemetry in real-time.")

if __name__ == "__main__":
    main()
