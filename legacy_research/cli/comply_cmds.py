# [C5-REAL] Exergy-Maximized
"""CORTEX CLI - Comply commands for sovereign governance & regulation."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    cli,
    console,
)
from cortex.compliance.tracker import ComplianceTracker
from cortex.compliance.comply_signer import ComplySigner


@click.group("comply")
def comply_cmds() -> None:
    """⚖️ CORTEX Comply - Enterprise governance & regulatory traceability."""


@comply_cmds.command("keys")
@click.argument("agent_id")
@click.option("--hex", "as_hex", is_flag=True, help="Export public key raw hex")
def keys_cmd(agent_id: str, as_hex: bool) -> None:
    """Retrieve or generate Ed25519 cryptographic keys for an agent."""
    signer = ComplySigner()
    try:
        _, _ = signer.get_or_create_agent_keys(agent_id)
        pub_hex = signer.export_public_key_hex(agent_id)
        
        if as_hex:
            click.echo(pub_hex)
            return

        priv_path = signer.keys_dir / f"{agent_id.replace(':', '_')}_private.pem"
        pub_path = signer.keys_dir / f"{agent_id.replace(':', '_')}_public.pem"

        console.print(f"\n[bold #00f3ff]Ed25519 Provenance Identity - {agent_id}[/bold #00f3ff]")
        console.print(f"  [bold]Public Key (Hex):[/]  {pub_hex}")
        console.print(f"  [bold]Private Key Path:[/]  {priv_path}")
        console.print(f"  [bold]Public Key Path:[/]   {pub_path}\n")
    except Exception as e:
        raise click.ClickException(f"Failed to manage keys: {e}")


@comply_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def verify_cmd(db: str) -> None:
    """Verify cryptographic integrity of the decision ledger and agent signatures."""
    tracker = ComplianceTracker(db_path=db)
    try:
        res = tracker.verify_chain()
        
        title = "⚖️ CORTEX Ledger Verification Status"
        if res.get("valid", False):
            border_style = "green"
            status_text = "[bold green]✔ LKRGSER INTEGRITY VALID[/bold green]"
        else:
            border_style = "red"
            status_text = "[bold red]✖ TAMPERING OR SIGNATURE FAILURE DETECTED[/bold red]"

        body = (
            f"Status: {status_text}\n\n"
            f"Transactions Checked: {res.get('tx_checked', 0)}\n"
            f"Merkle Roots Checked: {res.get('roots_checked', 0)}\n"
            f"Signatures Verified:  {res.get('signatures_verified', 0)}"
        )

        violations = res.get("violations", [])
        if violations:
            body += "\n\n[bold red]Violations Found:[/bold red]"
            for i, v in enumerate(violations, 1):
                body += f"\n  {i}. type={v.get('type')}, fact_id={v.get('fact_id')}, reason={v.get('reason')}"

        console.print(Panel(body, title=title, border_style=border_style))
    except Exception as e:
        raise click.ClickException(f"Verification failed: {e}")
    finally:
        tracker.close()


@comply_cmds.command("audit")
@click.option("--project", "-p", default="default", help="Project namespace")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--format", "fmt", type=click.Choice(["json", "markdown"]), default="markdown", help="Report format")
@click.option("--output", "-o", type=click.Path(writable=True, path_type=Path), default=None, help="Output file path")
def audit_cmd(project: str, db: str, fmt: str, output: Path | None) -> None:
    """Generate and export an EU AI Act Article 12 compliance report."""
    tracker = ComplianceTracker(db_path=db, project=project)
    try:
        report = tracker.export_audit(project=project, include_facts=True)
        eu = report.get("eu_ai_act", {})
        integrity = report.get("integrity", {})
        summary = report.get("facts_summary", {})

        if fmt == "json":
            report_str = json.dumps(report, indent=2)
        else:
            # Build markdown compliance report
            report_str = (
                f"# CORTEX COMPLIANCE REPORT: EU AI Act Article 12\n\n"
                f"* **Regulation:** {eu.get('regulation')}\n"
                f"* **Scoping:** {eu.get('article')} (Record-Keeping)\n"
                f"* **Enforcement Date:** {eu.get('enforcement_date')}\n"
                f"* **Status:** **{eu.get('status')}** (Score: {eu.get('score')})\n"
                f"* **Generated At:** {report.get('generated_at')}\n"
                f"* **Project:** `{report.get('project')}`\n\n"
                f"## 🏛️ Regulation Sub-Requirement Checks\n\n"
            )
            for k, check in eu.get("checks", {}).items():
                status = "🟢 COMPLIANT" if check.get("compliant") else "🔴 NON-COMPLIANT"
                report_str += (
                    f"### {k.replace('_', ' ').title()}\n"
                    f"* **Status:** {status}\n"
                    f"* **Rule:** {check.get('description')}\n"
                    f"* **Evidence:** {check.get('evidence')}\n\n"
                )

            report_str += (
                f"## 🔒 Cryptographic Integrity Details\n\n"
                f"* **Chain Valid:** {integrity.get('valid')}\n"
                f"* **Transactions Checked:** {integrity.get('tx_checked')}\n"
                f"* **Merkle Roots Checked:** {integrity.get('roots_checked')}\n"
                f"* **Agent Signatures Verified:** {integrity.get('signatures_verified')}\n\n"
                f"## 📊 Facts Statistics Summary\n\n"
                f"* **Total Facts:** {summary.get('total_facts')}\n"
                f"* **Active Facts:** {summary.get('active_facts')}\n"
                f"* **Deprecated Facts:** {summary.get('deprecated_facts')}\n"
                f"* **Distinct Agent Sources:** {', '.join(summary.get('sources', [])) or 'None'}\n"
            )

        if output:
            output.write_text(report_str, encoding="utf-8")
            console.print(f"[bold green]✔[/bold green] Compliance report written to: [dim]{output}[/dim]")
        else:
            if fmt == "json":
                click.echo(report_str)
            else:
                # Render beautifully to console using tables
                console.print(f"\n[bold #00f3ff]⚖️ {eu.get('regulation')} Compliance Report - {project}[/bold #00f3ff]")
                console.print(f"  [bold]Status:[/]    [green]{eu.get('status')}[/] (Score: {eu.get('score')})")
                console.print(f"  [bold]Timestamp:[/] {report.get('generated_at')}\n")

                table = Table(title="Article 12 Requirements", border_style="dim")
                table.add_column("Rule", style="cyan")
                table.add_column("Requirement Description", style="dim")
                table.add_column("Status", style="bold")
                table.add_column("Evidence", style="green")

                for k, check in eu.get("checks", {}).items():
                    status = "[green]COMPLIANT[/]" if check.get("compliant") else "[red]NON_COMPLIANT[/]"
                    table.add_row(
                        k.replace("art_12_", "").replace("_", " ").title(),
                        check.get("description"),
                        status,
                        check.get("evidence"),
                    )
                console.print(table)
                console.print()
    except Exception as e:
        raise click.ClickException(f"Failed to generate audit: {e}")
    finally:
        tracker.close()


# Dynamically register commands to root Click group
cli.add_command(comply_cmds)
