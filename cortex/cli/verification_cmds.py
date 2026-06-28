# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from cortex.cli.common import cli
from cortex.verification.verifier import SovereignVerifier

console = Console()


@cli.command("verify-files")
@click.argument("files", nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=False))
def verify_files_cmd(files: tuple[str, ...]) -> None:
    """Verifica archivos Python contra los invariantes de seguridad soberanos."""
    if not files:
        console.print("[yellow]No se especificaron archivos para verificar.[/]")
        return

    verifier = SovereignVerifier()
    all_valid = True

    table = Table(
        title="Formal Verification Results (Z3 + AST)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("File", style="cyan")
    table.add_column("Result", style="bold")
    table.add_column("Violation Details", style="red")

    for file_path in files:
        if not file_path.endswith(".py"):
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()

            result = verifier.check(code, {"file_path": file_path})
            if result.is_valid:
                table.add_row(file_path, "[green]PASSED[/]", "[dim]Zero violations[/]")
            else:
                all_valid = False
                violations_str = "\n".join(
                    [f"- [{v['id']}] {v['message']}" for v in result.violations]
                )
                table.add_row(file_path, "[red]FAILED[/]", violations_str)
        except (ValueError, TypeError, OSError, KeyError) as e:
            all_valid = False
            table.add_row(file_path, "[red]CRASHED[/]", f"Read/processing error: {str(e)}")

    console.print(table)

    if not all_valid:
        console.print("\n[bold red]❌ FORMAL VERIFICATION FAILED. Blocking integration.[/]")
        raise click.exceptions.Exit(1)

    console.print("\n[bold green]✓ FORMAL VERIFICATION COMPLETED SUCCESSFULLY.[/]")


@cli.command("verify-ledger")
@click.option("--db-path", default=None, help="Path to the cortex SQLite DB")
def verify_ledger_cmd(db_path: str | None) -> None:
    """Cryptographically verifies the offline integrity of the CORTEX Ledger (H5.1)."""
    import asyncio

    from cortex.compliance.tracker import ComplianceTracker

    console.print("[bold cyan]Starting offline audit of the Sovereign Ledger...[/]")

    kwargs = {}
    if db_path:
        kwargs["db_path"] = db_path

    tracker = ComplianceTracker(**kwargs)
    try:
        result = asyncio.run(tracker.verify_chain_async())

        table = Table(title="Sovereign Ledger Audit", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row(
            "Status", "[green]VALID[/]" if result.get("valid") else "[red]COMPROMISED[/]"
        )
        table.add_row("Transactions", str(result.get("tx_checked", 0)))
        table.add_row("Merkle Nodes", str(result.get("roots_checked", 0)))

        console.print(table)

        if not result.get("valid"):
            console.print("[bold red]❌ CRYPTOGRAPHIC INTEGRITY FAILURE DETECTED.[/]")
            for v in result.get("violations", []):
                console.print(f"[red] - {v}[/]")
            raise click.exceptions.Exit(1)

        console.print("[bold green]✓ THE LEDGER IS CRYPTOGRAPHICALLY INTACT.[/]")

    finally:
        tracker.close()
