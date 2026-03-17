import asyncio
import logging

import click

from cortex.cli.common import DEFAULT_DB, console, get_engine
from cortex.extensions.swarm.josu_daemon import JosuProactiveDaemon

logger = logging.getLogger("cortex.cli.josu")


@click.group("josu")
def app():
    """Manage the JOSU proactive daemon."""
    pass


@app.command("start")
@click.option("--daemon-mode", is_flag=True, help="Run in pure background mode.")
def start_josu(daemon_mode: bool = False):
    """Start the multi-agent proactive daemon."""
    console.print("🤖 [bold cyan]Booting MOSKV-Josu Daemon...[/bold cyan]")
    engine = get_engine(DEFAULT_DB)
    josu = JosuProactiveDaemon(cortex_db=engine)

    try:
        asyncio.run(josu.proactive_loop())
    except KeyboardInterrupt:
        logger.info("JOSU Daemon shutdown safely via SIGINT.")
