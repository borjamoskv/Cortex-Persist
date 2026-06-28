# [C5-REAL] Exergy-Maximized
"""
Audit Commands
Commands for system security and architectural auditing.
"""

import asyncio

import click

from cortex.audit.frontier import FrontierAuditor
from cortex.cli.common import console, get_engine
from cortex.cli.trust_cmds import audit


@audit.command("frontier")
@click.option("--project", "-p", required=True, help="Target project name to evaluate.")
@click.option(
    "--model", "-m", help="Override default SovereignLLM with a specific preferred provider."
)
def frontier_cmd(project: str, model: str | None):
    """Execute a lethal cognitive audit using the TOM, OLIVER & BENJI triad."""
    console.print(
        f"[bold magenta]🐺 Awakening Frontier Auditor for project: {project}...[/bold magenta]"
    )

    engine = get_engine()
    auditor = FrontierAuditor(engine=engine, model_override=model)

    # Run standard Sovereign context
    with console.status("[cyan]Triad is dissecting local definitions...[/cyan]"):
        result = asyncio.run(auditor.run_audit(project))

    if result["status"] == "SUCCESS":
        console.print(
            f"[bold green]✔ Audit executed via {result['provider']} "
            f"({result['latency']:.0f}ms)[/bold green]"
        )
        console.print("\n[bold]⚖️ FRONTIER REPORT:[/bold]")
        console.print(result["report_markdown"])
    else:
        # Fallback or complete failure
        console.print(
            f"[bold red]❌ Critical failure during audit generation "
            f"({result['provider']})[/bold red]"
        )
        console.print(result["report_markdown"])


@audit.command("export")
@click.option(
    "--format",
    "-f",
    required=True,
    type=click.Choice(["eu-ai-act"]),
    help="Export format standard.",
)
@click.option("--out", "-o", default="audit_bundle.zip", help="Output zip file path.")
def export_cmd(format: str, out: str):
    """Export the Master Ledger to a verifiable compliance bundle."""
    console.print(
        f"[bold magenta]📦 Exporting {format.upper()} Compliance Bundle to {out}...[/bold magenta]"
    )

    from cortex.audit.compliance_bundle import ComplianceBundler

    # In a real CLI, we'd fetch the configured db path, but we'll use the default or typical local path.
    bundler = ComplianceBundler(db_path=".cortex/cortex_ledger.db")
    success = bundler.export_bundle(out)

    if success:
        console.print("[bold green]✔ Compliance bundle exported successfully.[/bold green]")
    else:
        console.print(
            "[bold red]❌ Failed to export compliance bundle. Check logs for details.[/bold red]"
        )


@audit.command("verify-bundle")
@click.option("--bundle", "-b", required=True, help="Path to the audit_bundle.zip")
@click.option("--public-key", "-k", required=True, help="Base64-encoded Ed25519 Public Key")
def verify_bundle_cmd(bundle: str, public_key: str):
    """Offline cryptographic verification of an EU AI Act compliance bundle."""
    console.print(
        f"[bold magenta]🔍 Initiating offline verification of bundle: {bundle}[/bold magenta]"
    )

    from cortex.audit.compliance_verifier import ComplianceVerifier

    verifier = ComplianceVerifier(bundle_path=bundle, public_key_b64=public_key)
    report = verifier.verify()

    if report["status"] == "VALID":
        console.print("[bold green]✔ Bundle Cryptographically Verified[/bold green]")
        console.print(f"  Records Verified: {report.get('records_verified')}")
        console.print(f"  Batches Verified: {report.get('batches_verified')}")
        console.print(f"  Details: {report.get('details')}")
    else:
        console.print(f"[bold red]❌ Verification Failed: {report['status']}[/bold red]")
        console.print(f"  Reason: {report.get('reason')}")
        import sys

        sys.exit(1)
