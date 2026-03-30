
"""
CORTEX v6 — Compliance Commands
EU AI Act Article 12 compliance interface.
"""

import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import console
from cortex.compliance import ComplianceTracker


@click.group("compliance")
def compliance():
    """⚖️ EU AI Act Compliance: Article 12 Tracking & PDF Proofs."""
    pass

@compliance.command("export")
@click.option("--project", "-p", default="default", help="Project to report on.")
@click.option("--pdf", is_flag=True, help="Export as Industrial Noir PDF.")
@click.option("--output", "-o", default="audit_report.pdf", help="PDF output path.")
def export_cmd(project: str, pdf: bool, output: str):
    """Generate an Article 12 compliance report for a project."""
    tracker = ComplianceTracker(project=project)

    with console.status(f"[bold cyan]Generating Article 12 report for '{project}'...[/bold cyan]"):
        report = tracker.export_audit(project=project)

    # UI Display
    eu = report["eu_ai_act"]
    status_style = "green" if eu["status"] == "COMPLIANT" else "red"

    console.print(Panel(
        f"[bold]{eu['regulation']}[/bold]\n"
        f"Article: {eu['article']}\n"
        f"Status: [{status_style}]{eu['status']}[/]\n"
        f"Score: {eu['score']}",
        title="[bold blue]Compliance Summary[/bold blue]",
        border_style=status_style
    ))

    table = Table(title=f"Article 12 Checks: {project}")
    table.add_column("Requirement", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Evidence")

    for key, check in eu["checks"].items():
        status = "[green]✔[/]" if check["compliant"] else "[red]✘[/]"
        table.add_row(check["description"], status, check["evidence"])

    console.print(table)

    if pdf:
        with console.status("[bold magenta]Forging Industrial Noir PDF...[/bold magenta]"):
            path = tracker.export_pdf(project=project, output_path=output)
            abs_path = os.path.abspath(path)
            console.print(f"\n[bold green]✔ PDF Proof generated:[/] [link=file://{abs_path}]{abs_path}[/link]")

    tracker.close()

@compliance.command("audit")
@click.option("--project", "-p", default="default", help="Project to verify.")
def verify_cmd(project: str):
    """Deep cryptographic verification of the decision ledger."""
    tracker = ComplianceTracker(project=project)

    with console.status("[bold yellow]Scanning ledger for tampering...[/bold yellow]"):
        result = tracker.verify_chain()

    if result["valid"]:
        console.print("[bold green]✔ Ledger Integrity Verified.[/bold green]")
        console.print(f"Transactions checked: {result['tx_checked']}")
        console.print(f"Merkle roots checked: {result['roots_checked']}")
    else:
        console.print("[bold red]❌ TAMPERING DETECTED![/bold red]")
        for v in result["violations"]:
            console.print(f"  - [red]{v['type']}[/] at ID {v['id']}")

    tracker.close()


@compliance.command("byzantine")
@click.option("--project", "-p", default="default", help="Project to audit.")
def byzantine_cmd(project: str):
    """Run a GPT-5.4 based semantic audit for anomaly detection."""
    tracker = ComplianceTracker(project=project)

    with console.status("[bold magenta]Invoking GPT-5.4 Byzantine Auditor...[/bold magenta]"):
        result = tracker.run_byzantine_audit(project=project)

    if "error" in result:
        console.print(f"[bold red]Error:[/] {result['error']}")
    else:
        console.print(Panel(
            result["report"],
            title="[bold magenta]Byzantine Audit Report (GPT-5.4)[/bold magenta]",
            border_style="magenta"
        ))
        if result["valid"]:
            console.print("[bold green]✔ No semantic anomalies detected at this scale.[/bold green]")
        else:
            console.print("[bold red]⚠ Semantic anomalies or drift detected![/bold red]")

    tracker.close()


@compliance.command("forensics")
def forensics_cmd():
    """Run out-of-band forensics to detect database-level tampering."""
    tracker = ComplianceTracker()

    with console.status("[bold blue]Performing out-of-band forensics scan...[/bold blue]"):
        result = tracker.run_forensics_scan()

    if result["drift_detected"]:
        console.print("[bold red]❌ FORGERY DETECTED![/bold red]")
        console.print(f"Transactions verified: {result['tx_checked']}")
        console.print(f"Drift point ID: [bold white]{result['drift_record_id']}[/bold white]")
        console.print(f"Expected hash: {result['expected_hash']}")
        console.print(f"Actual hash: {result['actual_hash']}")
    else:
        console.print("[bold green]✔ Database-level integrity verified.[/bold green]")
        console.print(f"Transactions verified: {result['tx_checked']}")

    tracker.close()
