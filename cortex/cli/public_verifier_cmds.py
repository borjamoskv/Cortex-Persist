from __future__ import annotations

import json

import click

from cortex.cli.common import cli
from cortex.ledger.public_verifier import verify_export


@cli.command("verify-ledger-export")
@click.argument("export_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def verify_ledger_export(export_dir: str) -> None:
    """Verify a public ledger export from files only."""
    report = verify_export(export_dir)
    click.echo(json.dumps(report, indent=2, sort_keys=True))

    if report["result"] == "INVALID":
        raise click.exceptions.Exit(1)
    if report["result"] == "VALID_WITH_LIMITATIONS":
        raise click.exceptions.Exit(2)
