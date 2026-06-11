# [C5-REAL] Exergy-Maximized
"""
moskv_aegis_cmds.py - CLI commands for Moskv-Aegis Adversarial Ledger.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import aiosqlite
import click
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.audit.moskv_aegis import MoskvAegisEngine

logger = logging.getLogger(__name__)


@click.group("moskv-aegis")
def moskv_aegis() -> None:
    """🛡️ Moskv-Aegis - Adversarial Ledger & Verification Engine."""
    pass


@moskv_aegis.command("audit")
@click.option("--db", "db_path", default=DEFAULT_DB, help="Path to SQLite database")
def run_audit(db_path: str) -> None:
    """Run an adversarial audit and anchor findings in the cryptographic ledger."""
    console.print(
        Panel(
            "[bold #FF0055]🛡️ MOSKV-AEGIS: ADVERSARIAL AUDIT PROTOCOL[/]",
            border_style="#CCFF00",
        )
    )

    async def _audit() -> None:
        async with aiosqlite.connect(db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()

            engine = MoskvAegisEngine(ledger)
            result = await engine.run_adversarial_audit()

            # Display Findings
            findings = result.get("findings", [])
            chains = result.get("exploit_chains", [])
            risk_score = result.get("risk_score", 0.0)

            console.print(f"\n[bold white]Risk Score:[/] [bold cyan]{risk_score:.4f}[/]")

            if findings:
                f_table = Table(title="[bold red]Structural Findings[/]", show_lines=True)
                f_table.add_column("Attack", style="magenta")
                f_table.add_column("Severity", style="red")
                f_table.add_column("Target", style="white")

                for f in findings:
                    f_table.add_row(
                        f.get("attack", "N/A"),
                        str(f.get("severity", "N/A")),
                        f.get("target", "N/A"),
                    )
                console.print(f_table)

            if chains:
                c_table = Table(title="[bold yellow]Exploit Chains[/]", show_lines=True)
                c_table.add_column("Chain Steps", style="yellow")
                
                for c in chains:
                    c_table.add_row(c)
                console.print(c_table)

            # Verification Output
            console.print("\n[bold green]✅ Audit Anchored to Ledger[/]")
            console.print(f"[dim]Audit ID: {result['audit_id']}[/]")
            console.print(f"[dim]Signature: {result['signature'][:64]}...[/]")
            console.print(f"[dim]Previous Hash: {result['prev_hash']}[/]")

    asyncio.run(_audit())


cli.add_command(moskv_aegis)
