# [C5-REAL] Exergy-Maximized
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


@worker_group.command(name="start")
@click.option("--db", default=None, help="Database path override")
@click.option("--poll", default=1.0, help="Poll interval in seconds")
def start_worker(db: str, poll: float):
    """Start all background workers (Enrichment, Compaction)."""
    import asyncio

    from cortex.worker.enrichment import EnrichmentWorker
    from cortex.worker.telemetry_compaction import TelemetryCompactionWorker

    db_path = db or DEFAULT_DB
    enrichment = EnrichmentWorker(db_path=db_path, poll_interval=poll)
    compaction = TelemetryCompactionWorker(
        db_path=db_path, poll_interval=30.0
    )  # check telemetry every 30s

    console.print("[bold noir.cyber]CORTEX Workers[/] starting...")

    async def run_workers():
        await asyncio.gather(enrichment.start(), compaction.start())

    try:
        _run_async(run_workers())
    except KeyboardInterrupt:
        console.print("\n[warning]Stopping workers...[/]")
        _run_async(enrichment.stop())
        _run_async(compaction.stop())
    except Exception as e:
        console.print(f"[danger]Worker crashed:[/] {e}")
