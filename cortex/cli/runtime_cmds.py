# [C5-REAL] Exergy-Maximized
import logging

import click

from cortex.cli.common import cli
from cortex.engine.runtime_kernel import CortexRuntime

logger = logging.getLogger(__name__)


@cli.command("daemon")
@click.option("--tick-delay", default=1.0, help="Delay between execution cycles in seconds.")
def run_cortex(tick_delay: float):
    """
    Start the Cortex Persist continuous runtime kernel.

    This command initiates the infinite Causal Execution Loop, activating the
    Snapshot Manager, Recovery Engine, and Prometheus Exporter.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    click.echo(f"🚀 Booting CORTEX Runtime Kernel (Tick: {tick_delay}s)")
    runtime = CortexRuntime()

    try:
        import decimal
        runtime.run_forever(tick_delay=decimal.Decimal(str(tick_delay)))  # type: ignore
    except KeyboardInterrupt:
        click.echo("\n🛑 Cortex Runtime interrupted by user. Shutting down gracefully.")
