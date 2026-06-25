# [C5-REAL] Exergy-Maximized
"""CORTEX Omega Daemon Command CLI interface.

Interactive terminal dashboard representing real-time Exergy and Shannon entropy levels.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cortex.cli.common import cli
from cortex.engine.omega_daemon import OmegaKernel

console = Console()
logger = logging.getLogger(__name__)


async def run_ui(kernel: OmegaKernel):
    # Colors
    _CYBER = "#CCFF00"
    _GOLD = "#D4AF37"
    _VIOLET = "#6600FF"
    _EMERALD = "#06d6a0"
    _DIM = "dim"
    _RED = "#FF3366"

    start_time = time.time()

    def make_layout() -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", size=10),
            Layout(name="footer"),
        )

        # Header
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header_text = Text()
        header_text.append("⚡ CORTEX OMEGA DAEMON", style=f"bold {_CYBER}")
        header_text.append("  ·  ", style=_DIM)
        header_text.append("C6-SOVEREIGN METABOLISM", style=f"bold {_GOLD}")
        header_text.append("  ·  ", style=_DIM)
        header_text.append(now, style=_DIM)
        layout["header"].update(Panel(header_text, border_style=_VIOLET, padding=(0, 1)))

        # Body split
        layout["body"].split_row(
            Layout(name="vitals"),
            Layout(name="sensors"),
        )

        # Vitals
        vitals_table = Table(show_header=False, box=None, padding=(0, 2))
        vitals_table.add_column("Metric", style=f"bold {_GOLD}", min_width=16)
        vitals_table.add_column("Value", style="white")

        uptime = int(time.time() - start_time)
        uptime_str = f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}"

        exergy = kernel.guard.current_exergy
        exergy_bar = "█" * min(int(exergy / 100), 10) + "░" * (10 - min(int(exergy / 100), 10))

        vitals_table.add_row("Status", f"[bold {_EMERALD}]● RUNNING[/]")
        vitals_table.add_row("Uptime", uptime_str)
        vitals_table.add_row("Cycle Count", f"#{kernel._cycle_count}")
        vitals_table.add_row("Tick Rate", f"{kernel.tick_rate}s")
        vitals_table.add_row("Current Exergy", f"[bold {_CYBER}]{exergy:.1f} J[/] [{exergy_bar}]")
        vitals_table.add_row("Exergy Budget", f"${kernel.guard.budget_usd:.2f}")

        layout["body"]["vitals"].update(
            Panel(
                vitals_table,
                title=f"[bold {_CYBER}]◉ METABOLIC VITALS[/]",
                border_style=_VIOLET,
                padding=(0, 1),
            )
        )

        # Sensors
        sensors_table = Table(show_header=False, box=None, padding=(0, 2))
        sensors_table.add_column("Sensor", style=f"bold {_GOLD}", min_width=18)
        sensors_table.add_column("Metric", style="white")

        entropy = kernel.last_entropy
        entropy_style = _EMERALD if entropy < 10.0 else (_GOLD if entropy < 50.0 else _RED)
        entropy_bar = "█" * min(int(entropy / 5), 10) + "░" * (10 - min(int(entropy / 5), 10))

        sensors_table.add_row("Scanned Files", f"{kernel.sensor.last_scan_files} python files")
        sensors_table.add_row("TO-DOs / FIX-MEs", f"[bold white]{kernel.sensor.last_scan_todos}[/]")
        sensors_table.add_row(
            "Ruff Violations", f"[bold {_RED}]{kernel.sensor.last_scan_violations}[/]"
        )
        sensors_table.add_row(
            "Structural Entropy", f"[bold {entropy_style}]{entropy:.2f} J[/] [{entropy_bar}]"
        )
        sensors_table.add_row(
            "Auto-Push Config",
            f"[{_CYBER}]ACTIVE[/]" if kernel.auto_push else f"[{_DIM}]DISABLED[/]",
        )

        layout["body"]["sensors"].update(
            Panel(
                sensors_table,
                title=f"[bold {_CYBER}]∿ ECOSYSTEM SENSORS[/]",
                border_style=_VIOLET,
                padding=(0, 1),
            )
        )

        # Footer
        events_table = Table(show_header=False, box=None, padding=(0, 1))
        events_table.add_column("Event", style="white")

        display_events = (
            kernel.events[-6:]
            if kernel.events
            else ["Homeostasis maintained. Waiting for next cycle..."]
        )
        while len(display_events) < 6:
            display_events.insert(0, "")

        for ev in display_events:
            events_table.add_row(ev)

        layout["footer"].update(
            Panel(
                events_table,
                title=f"[bold {_CYBER}]◷ METABOLIC EVENT LOG[/]",
                border_style=_VIOLET,
                padding=(0, 1),
            )
        )

        return layout

    with Live(make_layout(), refresh_per_second=4, screen=True) as live:
        while kernel._running:
            live.update(make_layout())
            await asyncio.sleep(0.25)


@cli.group("omega")
def omega_cmds():
    """Mega Hito 38: Omega Singularity (CORTEX v10.0 Metabolism)."""


@omega_cmds.command("start")
@click.option("--tick-rate", default=60, help="Latidos por segundo del metabolismo.")
@click.option("--auto-push", is_flag=True, help="Auto-push en cada mutación.")
def cmd_omega_start(tick_rate: int, auto_push: bool):
    """
    Inicia el metabolismo de CORTEX (Omega Singularity).
    """
    # Mute default logs to stdout if running UI, to avoid visual corruption
    logging.getLogger().handlers = [
        h for h in logging.getLogger().handlers if not isinstance(h, logging.StreamHandler)
    ]

    kernel = OmegaKernel(tick_rate_seconds=tick_rate, auto_push=auto_push)

    async def main():
        ui_task = asyncio.create_task(run_ui(kernel))
        kernel_task = asyncio.create_task(kernel.run_forever())
        await asyncio.gather(ui_task, kernel_task)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        kernel.stop()
        # Reset terminal screen and show shutdown message
        console.print(
            "\n[bold red]Terminación manual detectada. Hibernando Omega Daemon...[/bold red]"
        )


@omega_cmds.command("status")
def cmd_omega_status():
    """
    Consulta el estado del metabolismo.
    """
    console.print("[dim]Omega Daemon status request (Stub)[/dim]")
    console.print("[green]OmegaKernel is available for instantiation.[/green]")
