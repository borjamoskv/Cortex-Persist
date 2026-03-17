"""CORTEX v6.0 — Swarm Kanban Board (TUI).

A rich-based live dashboard to monitor Sovereign Swarm agents in real-time.
Listens to the CORTEX SignalBus for state changes.
"""

import sqlite3
import threading
import time
from collections import defaultdict
from typing import Any

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from cortex.extensions.signals.bus import SignalBus

console = Console()

# Defined Swarm States
STATE_INITIALIZING = "INITIALIZING"
STATE_PLANNING = "PLANNING"
STATE_ISOLATED = "ISOLATED_WORKTREE"
STATE_VERIFICATION = "WAITING_CI"
STATE_HALTED = "HALTED_FOR_HUMAN"
STATE_COMPLETED = "COMPLETED"

STATE_COLORS = {
    STATE_INITIALIZING: "dim",
    STATE_PLANNING: "blue",
    STATE_ISOLATED: "yellow",
    STATE_VERIFICATION: "magenta",
    STATE_HALTED: "bold red blink",
    STATE_COMPLETED: "bold green",
}


class SwarmBoard:
    """TUI Kanban Board for observing the Swarm."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self.bus = SignalBus(self._conn)

        # Agent state tracking: source -> state dict
        self.agents: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "state": STATE_INITIALIZING,
                "task": "Booting...",
                "last_seen": time.time(),
                "failures": 0,
            }
        )
        self._running = False
        self._stop_event = threading.Event()

    def fetch_latest_signals(self):
        """Poll the bus for new events related to swarm state."""
        # Polling events without consuming them globally (using peek)
        # We only care about signals in the last few seconds to catch up,
        # or we just consume them with a specific TUI consumer name.
        signals = self.bus.poll(consumer="swarm_kanban_tui", limit=100)

        for sig in signals:
            source = sig.source
            if not source.startswith("agent:") and not source.startswith("josu"):
                continue

            event = sig.event_type
            payload = sig.payload

            # Map events to states
            if event == "swarm:plan":
                self.agents[source]["state"] = STATE_PLANNING
                self.agents[source]["task"] = payload.get("task", "Planning...")
            elif event == "swarm:worktree_enter":
                self.agents[source]["state"] = STATE_ISOLATED
                self.agents[source]["task"] = f"Wt: {payload.get('branch', 'unknown')}"
            elif event == "swarm:verify":
                self.agents[source]["state"] = STATE_VERIFICATION
                self.agents[source]["task"] = "Running tests..."
            elif event == "swarm:halt":
                self.agents[source]["state"] = STATE_HALTED
                self.agents[source]["task"] = payload.get("reason", "Human Intervention Required")
            elif event == "swarm:complete":
                self.agents[source]["state"] = STATE_COMPLETED
                self.agents[source]["task"] = payload.get("result", "Done")
            elif event == "swarm:error":
                self.agents[source]["failures"] += 1

            self.agents[source]["last_seen"] = time.time()

    def generate_layout(self) -> Layout:
        """Create the Rich layout."""
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
        )

        layout["header"].update(
            Panel(
                "[bold #CCFF00]CORTEX SWARM KANBAN BOARD[/] | [dim]Real-time agent telemetry[/]",
                border_style="#6600FF",
            )
        )

        # Build lanes
        lanes = {
            "PLANNING": Table(show_header=False, expand=True, box=box.SIMPLE),
            "EXECUTING": Table(show_header=False, expand=True, box=box.SIMPLE),
            "VERIFYING": Table(show_header=False, expand=True, box=box.SIMPLE),
            "HALTED": Table(show_header=False, expand=True, box=box.SIMPLE),
        }

        for table in lanes.values():
            table.add_column("Agent", style="cyan", width=15)
            table.add_column("Task")

        for source, data in self.agents.items():
            state = data["state"]
            color = STATE_COLORS.get(state, "white")
            row = (f"[{color}]{source}[/]", f"[dim]{data['task']}[/]")

            if state in (STATE_INITIALIZING, STATE_PLANNING):
                lanes["PLANNING"].add_row(*row)
            elif state == STATE_ISOLATED:
                lanes["EXECUTING"].add_row(*row)
            elif state == STATE_VERIFICATION:
                lanes["VERIFYING"].add_row(*row)
            elif state == STATE_HALTED:
                lanes["HALTED"].add_row(*row)

        # Split main into 4 columns
        layout["main"].split_row(
            Layout(Panel(lanes["PLANNING"], title="[blue]PLANNING", border_style="blue")),
            Layout(
                Panel(lanes["EXECUTING"], title="[yellow]ISOLATED (EXEC)", border_style="yellow")
            ),
            Layout(Panel(lanes["VERIFYING"], title="[magenta]CI / VERIFY", border_style="magenta")),
            Layout(
                Panel(lanes["HALTED"], title="[bold red blink]HALTED (HUMAN)", border_style="red")
            ),
        )

        return layout

    def start(self):
        """Run the live dashboard."""
        self._running = True
        try:
            with Live(self.generate_layout(), refresh_per_second=4, screen=True) as live:
                while self._running:
                    self.fetch_latest_signals()
                    live.update(self.generate_layout())
                    self._stop_event.wait(0.5)
        except KeyboardInterrupt:
            self._running = False
            console.print("[dim]Swarm Board terminated.[/]")


if __name__ == "__main__":
    board = SwarmBoard("/Users/borjafernandezangulo/.cortex/cortex.db")
    board.start()
