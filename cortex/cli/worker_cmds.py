"""
Worker commands for background enrichment.
"""

from __future__ import annotations

import logging

import click

from cortex.cli.common import DEFAULT_DB, _run_async, console

logger = logging.getLogger("cortex")


@click.group(name="worker")
def worker_group():
    """Manage background workers (Enrichment, etc)."""
    pass


@worker_group.command(name="start")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--poll", default=1.0, help="Polling interval in seconds")
def start_worker(db: str, poll: float):
    """Start the enrichment worker sidecar."""
    from cortex.worker.enrichment import EnrichmentWorker

    worker = EnrichmentWorker(db_path=db, poll_interval=poll)

    console.logger.info("[bold noir.cyber]CORTEX Enrichment Worker[/] starting...")
    console.logger.info(f"  [dim]Database:[/] {db}")
    console.logger.info(f"  [dim]Interval:[/] {poll}s")
    console.logger.info()

    try:
        _run_async(worker.start())
    except KeyboardInterrupt:
        console.logger.info("\n[warning]Stopping worker...[/]")
        _run_async(worker.stop())
    except Exception as e:
        console.logger.info(f"[danger]Worker crashed:[/] {e}")
