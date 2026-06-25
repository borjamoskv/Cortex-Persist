# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json

import click

from legacy_research.cli.common import cli
from legacy_research.ledger.public_verifier import verify_export


@cli.command("verify-ledger-export")
@click.argument("export_path", type=click.Path(exists=True, file_okay=True, dir_okay=True))
def verify_ledger_export(export_path: str) -> None:
    """Verify a public ledger export from files only."""
    report = verify_export(export_path)
    click.echo(json.dumps(report, indent=2, sort_keys=True))

    result = report["result"]
    if result == "INVALID":
        raise click.exceptions.Exit(1)
    if result in {"VALID_INTEGRITY_ONLY", "VALID_WITH_LIMITATIONS"}:
        raise click.exceptions.Exit(6)
