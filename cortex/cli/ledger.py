"""Sovereign Ledger CLI commands for CORTEX (Waves 5 & 6)."""

from __future__ import annotations

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, cli
from cortex.database.core import connect as db_connect
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.services.trust import TrustService

console = Console()

_FULL_VERIFY_REPORT_CAP = 10


@click.group(name="ledger")
def ledger_cmds():
    """Sovereign Ledger Operations (Wave 6: High-Performance Chaining)."""
    pass


def _verify_fact_integrity(db: str) -> dict[str, object]:
    """Run fact-level integrity checks used by the CLI full verify mode."""
    conn = None
    with TrustService(db) as trust:
        try:
            conn = db_connect(db)
            fact_count = int(conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] or 0)
        finally:
            if conn:
                conn.close()

        checks = trust.verify_batch(limit=max(fact_count, 1)) if fact_count else []

    violations = [
        f"Fact #{check.fact_id} ({check.project or 'unknown'}): {check.violation or 'UNKNOWN_VIOLATION'}"
        for check in checks
        if not check.valid
    ]
    return {
        "valid": len(violations) == 0,
        "checked_facts": fact_count,
        "violations": violations[:_FULL_VERIFY_REPORT_CAP],
        "total_violations": len(violations),
    }


@ledger_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--full", is_flag=True, help="Perform full cryptographic verify")
def verify_ledger(db: str, full: bool):
    """Verify hash chain integrity."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)
    fact_integrity: dict[str, object] | None = None

    with console.status("[bold cyan]Verifying ledger integrity..."):
        result = verifier.verify_chain()
        if full:
            fact_integrity = _verify_fact_integrity(db)

    ledger_valid = bool(result["valid"])
    facts_valid = True if fact_integrity is None else bool(fact_integrity["valid"])
    overall_valid = ledger_valid and facts_valid

    if overall_valid:
        console.print(
            f"[bold green]Ledger is VALID[/bold green] ({result['checked_events']} events checked)"
        )
        stats = result.get("enrichment_stats", {})
        console.print(
            f"Enrichment: [green]Indexed: {stats.get('indexed', 0)}[/green] | "
            f"[yellow]Pending: {stats.get('pending', 0)}[/yellow] | "
            f"[red]Failed: {stats.get('failed', 0)}[/red]"
        )
        if fact_integrity is not None:
            console.print(
                f"Fact Integrity: [green]OK[/green] "
                f"({fact_integrity['checked_facts']} facts checked)"
            )
    else:
        violations = list(result["violations"])
        if fact_integrity is not None:
            violations.extend(fact_integrity["violations"])
        console.print(f"[bold red]Ledger is COMPROMISED[/bold red]: {len(violations)} violations")
        for v in violations[:10]:
            console.print(f"  - {v}")
        if fact_integrity is not None:
            console.print(
                "Fact Integrity: "
                f"[red]COMPROMISED[/red] "
                f"({fact_integrity['total_violations']} invalid / "
                f"{fact_integrity['checked_facts']} checked)"
            )


@ledger_cmds.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--batch", default=10, help="Events per checkpoint")
def create_checkpoint(db: str, batch: int):
    """Compute and store a Merkle root for uncheckpointed events."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)

    with console.status("[bold cyan]Creating Merkle checkpoint..."):
        root_id = verifier.create_checkpoint(batch_size=batch)

    if root_id:
        console.print(f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}")
    else:
        console.print(
            "[yellow]No new events available for checkpointing (batch size not reached).[/yellow]"
        )


ledger_cmds_click = ledger_cmds
cli.add_command(ledger_cmds, name="trust-ledger")
