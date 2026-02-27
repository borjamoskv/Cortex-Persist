"""
CORTEX REACTOR (SYNAPSE-X) v1.0
The 'Killer Feature' for Marketing.
Visualizes Synaptic Resonance and Entropy Eradication.
"""

import random
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Industrial Noir Palette
CYBER_LIME = "#CCFF00"
ELECTRIC_VIOLET = "#6600FF"
ABYSSAL_BLACK = "#0A0A0A"
YINMN_BLUE = "#2E5090"


def create_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="reactor", ratio=2),
        Layout(name="entropy_feed", ratio=1),
    )
    return layout


class ReactorState:
    def __init__(self):
        self.resonance = 0.0
        self.entropy_count = 0
        self.logs = []
        self.healed_snippets = [
            "except Exception: -> except OSError:",
            "time.sleep(1) -> await asyncio.sleep(1)",
            "import web3 -> [INTERCEPTED]",
            "Complex branch (depth 12) -> Refactored",
            "Bare except found -> Added context",
            "Security vulnerability (exec) -> Nullified",
        ]

    def update(self):
        self.resonance = max(0.01, min(1.0, self.resonance + random.uniform(-0.1, 0.15)))
        if random.random() > 0.8:
            self.entropy_count += 1
            snippet = random.choice(self.healed_snippets)
            self.logs.append(
                f"[{time.strftime('%H:%M:%S')}] {CYBER_LIME}HEALED:{ELECTRIC_VIOLET} {snippet}"
            )
            if len(self.logs) > 10:
                self.logs.pop(0)


def generate_reactor_view(state: ReactorState) -> Panel:
    resonance_pct = int(state.resonance * 100)
    color = CYBER_LIME if state.resonance < 0.7 else ELECTRIC_VIOLET

    table = Table.grid(expand=True)
    table.add_row(f"[{color}]SYNAPTIC RESONANCE[/] [white]v2.0[/]")
    table.add_row(f"[bold {color}]{resonance_pct}%[/] PRESSURE")

    # Simple ASCII visualization of the "Mind"
    brain = Text("\n", justify="center")
    brain.append("   .---.\n", style=color)
    brain.append("  /     \\\n", style=color)
    brain.append(" ( () () )\n", style=color)
    brain.append("  \\  -  /\n", style=color)
    brain.append("   '---'\n", style=color)

    return Panel(
        table,
        title="[white]CØRTEX REACTOR[/]",
        border_style=color,
        subtitle=f"[{CYBER_LIME}]Entropy Crushed: {state.entropy_count}[/]",
    )


def generate_feed_view(state: ReactorState) -> Panel:
    feed_text = Text("\n".join(state.logs))
    return Panel(
        feed_text, title=f"[{ELECTRIC_VIOLET}]ENTROPY FEED[/]", border_style=ELECTRIC_VIOLET
    )


def run_reactor():
    layout = create_layout()
    state = ReactorState()

    layout["header"].update(
        Panel(
            f"[bold {CYBER_LIME}]CORTEX SOVEREIGN MEMORY[/] | {YINMN_BLUE}Mode: Apotheosis-∞",
            border_style=YINMN_BLUE,
        )
    )
    layout["footer"].update(
        Panel(
            "[dim white]Axiom 7: If it works but isn't beautiful, it's wrong.[/]",
            border_style=YINMN_BLUE,
        )
    )

    with Live(layout, refresh_per_second=4, screen=True):
        while True:
            state.update()
            layout["reactor"].update(generate_reactor_view(state))
            layout["entropy_feed"].update(generate_feed_view(state))
            time.sleep(0.2)


if __name__ == "__main__":
    try:
        run_reactor()
    except KeyboardInterrupt:
        pass
