#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
# SPDX-License-Identifier: Apache-2.0
"""
CORTEX - SWARM DASHBOARD (VOID-BEYOND).

Real-time TUI for monitoring the Legion 10,000 swarm.
Visualizes reputation slashing, consensus alignment, and exergy extraction.
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

# ── SOVEREIGN PATH ANCHOR ──
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "cortex.db"

console = Console()


def get_swarm_status():
    """Fetches agent status from the local ledger."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, reputation_score, alignment_hits, alignment_misses "
            "FROM agents WHERE is_active = 1 ORDER BY id LIMIT 100"
        )
        agents = cursor.fetchall()

        cursor = conn.execute("SELECT count(1) FROM facts")
        fact_count = cursor.fetchone()[0]

        conn.close()
        return agents, fact_count
    except Exception:
        return [], 0


def make_grid(agents):
    """Generates the 10x10 visual grid."""
    grid_table = Table.grid(expand=True)
    for _ in range(10):
        grid_table.add_column(justify="center")

    for i in range(0, 100, 10):
        row_cells = []
        for j in range(10):
            idx = i + j
            if idx < len(agents):
                rep = agents[idx]["reputation_score"]
                if rep > 0.9:
                    char = "[bold green]💎[/]"
                elif rep > 0.5:
                    char = "[yellow]⚪[/]"
                else:
                    char = "[bold red]💀[/]"
                row_cells.append(char)
            else:
                row_cells.append("[dim]◌[/]")
        grid_table.add_row(*row_cells)
    return grid_table


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="grid", ratio=2),
        Layout(name="stats", ratio=1),
    )
    return layout


async def main():
    layout = make_layout()

    with Live(layout, refresh_per_second=2, screen=True):
        while True:
            agents, fact_count = get_swarm_status()

            # Header
            layout["header"].update(
                Panel(
                    f"[bold blue]VOID-BEYOND Swarm Monitor[/] | "
                    f"Exergy: 100% | Time: {datetime.now().strftime('%H:%M:%S')}",
                    border_style="blue",
                )
            )

            # Grid
            layout["grid"].update(
                Panel(
                    make_grid(agents),
                    title="[bold]Legion 100 Grid (Reputation Pulse)[/]",
                    border_style="white",
                )
            )

            # Stats
            stats_table = Table(show_header=False, expand=True)
            stats_table.add_row("Total Facts", str(fact_count))
            stats_table.add_row("Active Agents", str(len(agents)))

            slashed = sum(1 for a in agents if a["reputation_score"] < 0.5)
            stats_table.add_row("Slashed Nodes", f"[bold red]{slashed}[/]")

            layout["stats"].update(
                Panel(stats_table, title="[bold]Cortex Metrics[/]", border_style="magenta")
            )

            # Footer
            layout["footer"].update(
                Panel(
                    "[dim]Press Ctrl+C to exit. Monitoring VOID-BEYOND alignment...[/]",
                    border_style="blue",
                )
            )

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        import logging

        pass
