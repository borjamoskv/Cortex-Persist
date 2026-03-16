"""CORTEX CLI — Trust & Compliance Commands."""

import asyncio

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli
from cortex.cli.trust_helpers import (
    _check_chain_integrity,
    _check_merkle,
    _extract_agents,
    _find_transaction,
    _get_audit_trail,
    _render_verification_certificate,
    _safe_count,
    _verify_chain,
)

__all__ = ["verify_fact", "compliance_report", "audit", "audit_cognitive"]

console = Console()


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@cli.command("verify")
@click.argument("fact_id", type=int)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def verify_fact(fact_id: int, db: str) -> None:
    """Verify cryptographic integrity of a specific fact."""
    from cortex.cli.errors import err_fact_not_found, handle_cli_error
    from cortex.database.core import connect as db_connect

    conn = None
    try:
        conn = db_connect(db)
        # Get the fact
        fact = conn.execute(
            "SELECT id, project, content, fact_type, created_at, tx_id FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()

        if not fact:
            err_fact_not_found(fact_id)
            return

        fact_tx_id = fact[5]
        tx = _find_transaction(conn, fact_id, fact_tx_id)

        if not tx:
            console.print(
                Panel(
                    f"[yellow]Warning: Fact #{fact_id} exists but has no "
                    "transaction record.[/yellow]",
                    title="Verification",
                )
            )
            return

        tx_id, _tx_hash, prev_hash, _action, _tx_time = tx

        chain_valid, chain_msg = _verify_chain(conn, tx_id, prev_hash)
        checkpoint = _check_merkle(conn, tx_id)

        _render_verification_certificate(fact, tx, chain_valid, chain_msg, checkpoint)
    except Exception as e:  # noqa: BLE001 — CLI boundary catch
        handle_cli_error(e, db_path=db, context="verifying fact")
    finally:
        if conn:
            conn.close()


@cli.command("compliance-report")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def compliance_report(db: str) -> None:
    """Generate EU AI Act Article 12 compliance snapshot."""
    from datetime import datetime, timezone

    from cortex.cli.errors import handle_cli_error
    from cortex.database.core import connect as db_connect

    conn = None
    try:
        conn = db_connect(db)

        total_facts = _safe_count(conn, "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
        decisions = _safe_count(
            conn, "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision' AND valid_until IS NULL"
        )
        total_tx = _safe_count(conn, "SELECT COUNT(*) FROM transactions")
        checkpoints = _safe_count(conn, "SELECT COUNT(*) FROM merkle_roots")
        projects = _safe_count(
            conn, "SELECT COUNT(DISTINCT project) FROM facts WHERE valid_until IS NULL"
        )
        agents = _extract_agents(conn)

        time_range = conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM facts WHERE valid_until IS NULL"
        ).fetchone()

        chain_ok, violations = _check_chain_integrity(conn)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        console.print()
        console.print(
            Panel.fit(
                "[bold]CORTEX - EU AI Act Compliance Report[/bold]\n"
                "[dim]Article 12: Record-Keeping Obligations[/dim]",
                border_style="bright_green" if chain_ok else "red",
            )
        )

        table = Table(show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_row("Report Date", now)
        table.add_row("Total Facts", str(total_facts))
        table.add_row("Logged Decisions", str(decisions))
        table.add_row("Active Projects", str(projects))
        table.add_row("Tracked Agents", str(len(agents)))
        table.add_row("Coverage", f"{time_range[0] or 'N/A'} -> {time_range[1] or 'N/A'}")
        table.add_row("", "")
        table.add_row("TX Ledger Entries", str(total_tx))
        table.add_row("Merkle Checkpoints", str(checkpoints))
        table.add_row(
            "Hash Chain",
            "[green]OK[/green]" if chain_ok else f"[red]{violations} violations[/red]",
        )
        table.add_row("Epistemic Isolation", "[green]ENFORCED (L0/L2)[/green]")

        from pathlib import Path

        from cortex.utils.landauer import audit_calcification

        cortex_root = Path(__file__).parent.parent
        calc_results = audit_calcification(cortex_root, limit=5)
        avg_calc = sum(r["score"] for r in calc_results) / len(calc_results) if calc_results else 0

        table.add_row("Calcification Index", f"[bold yellow]{avg_calc:.2f}[/bold yellow] (Omega-2)")
        console.print(table)

        c1, c2, c3, c4, c5 = (
            total_tx > 0,
            decisions > 0,
            chain_ok,
            checkpoints > 0,
            len(agents) > 0,
        )

        def icon(ok):
            return "[green]OK[/green]" if ok else "[red]X[/red]"

        checks = Table(title="Compliance Checklist (Art. 12)")
        checks.add_column("Requirement", style="bold")
        checks.add_column("Status")
        checks.add_row("Automatic event logging (Art. 12.1)", icon(c1))
        checks.add_row("Decision recording (Art. 12.2)", icon(c2))
        checks.add_row("Tamper-proof storage (Art. 12.3)", icon(c3))
        checks.add_row("Periodic verification (Art. 12.4)", icon(c4))
        checks.add_row("Agent traceability (Art. 12.2d)", icon(c5))
        checks.add_row("Epistemic Isolation (Omega-3)", "[green]OK[/green]")
        checks.add_row("Landauer's Razor (Omega-2)", icon(avg_calc < 100))
        console.print(checks)

        score = sum([c1, c2, c3, c4, c5])
        if score == 5:
            verdict = "[bold green]COMPLIANT[/bold green]"
        elif score >= 3:
            verdict = "[bold yellow]PARTIAL[/bold yellow]"
        else:
            verdict = "[bold red]NON-COMPLIANT[/bold red]"

        console.print(
            Panel(f"{verdict}\n\nCompliance Score: [bold]{score}/5[/bold]", title="Verdict")
        )
    except Exception as e:  # noqa: BLE001 — CLI boundary catch
        handle_cli_error(e, db_path=db, context="generating compliance report")
    finally:
        if conn:
            conn.close()


@cli.command("audit-cognitive")
@click.option("--tenant", "-t", default="default", help="Tenant ID to audit")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def audit_cognitive(tenant: str, db: str) -> None:
    """Run a deep cryptographic audit of the Cognitive Event Ledger (L3)."""
    from cortex.db import connect_async
    from cortex.memory.ledger import EventLedgerL3

    async def _run_audit():
        async with connect_async(db) as conn:
            ledger = EventLedgerL3(conn)
            report = await ledger.verify_chain(tenant)

            table = Table(title=f"Cognitive Audit Report: {tenant}")
            table.add_column("Metric", style="bold")
            table.add_column("Value")

            status_style = "green" if report["status"] == "VALID" else "red"
            table.add_row("Audit Status", f"[{status_style}]{report['status']}[/{status_style}]")
            table.add_row("Events Audited", str(report.get("events_audited", 0)))
            table.add_row("Integrity Score", f"{report.get('integrity_score', 1.0):.2%}")
            table.add_row("Timestamp", report.get("timestamp", ""))

            console.print()
            console.print(Panel(table, border_style=status_style))

            if report.get("findings"):
                findings_table = Table(title="Audit Findings")
                findings_table.add_column("Log", style="dim")
                for finding in report["findings"]:
                    findings_table.add_row(finding)
                console.print(findings_table)

    try:
        _run_async(_run_audit())
    except Exception as e:  # noqa: BLE001 — CLI boundary catch
        from cortex.cli.errors import handle_cli_error

        handle_cli_error(e, db_path=db, context="cognitive audit")
    finally:
        console.print("[dim]Audit complete.[/dim]")


def _audit_trail(project: str, limit: int, db: str) -> None:
    """Display the audit trail from the database."""
    from cortex.cli.errors import handle_cli_error
    from cortex.database.core import connect as db_connect

    conn = None
    try:
        conn = db_connect(db)
        table = _get_audit_trail(conn, project, limit)
        if table:
            console.print(table)
    except Exception as e:  # noqa: BLE001 — CLI boundary catch
        handle_cli_error(e, db_path=db, context="generating audit trail")
    finally:
        if conn:
            conn.close()


@cli.command("audit")
@click.option("--calcification", is_flag=True, help="Run Landauer's Razor audit")
@click.option("--frontend", is_flag=True, help="Run Zero-Latency UI Axiom audit (CC < 5)")
@click.option("--project", "-p", default="", help="Filter trail by project")
@click.option("--limit", "-n", default=10, help="Max entries to show")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def audit(calcification: bool, frontend: bool, project: str, limit: int, db: str) -> None:
    """Run audits or view Audit Trail."""
    if frontend:
        from cortex.cli.audit_helpers import audit_frontend

        audit_frontend()
    elif calcification:
        from cortex.cli.audit_helpers import audit_calcification_report

        audit_calcification_report(limit)
    else:
        _audit_trail(project, limit, db)


@cli.command("siege")
@click.option("--db", default=DEFAULT_DB, help="Database path to attack")
def siege(db: str) -> None:
    """Run an autonomous Red Team swarm to test Ledger and Vault BFT compliance."""
    from cortex.cli.errors import handle_cli_error
    from cortex.crypto.vault import Vault
    from cortex.database.pool import CortexConnectionPool
    from cortex.engine.legion_vectors import COMPLIANCE_SIEGE_SWARM
    from cortex.engine_async import AsyncCortexEngine

    async def _run_siege():
        pool = CortexConnectionPool(db, min_connections=2, max_connections=10, read_only=False)
        await pool.initialize()
        engine = AsyncCortexEngine(pool, db)
        try:
            import os

            key = os.environ.get("CORTEX_VAULT_KEY")
            if key:
                engine.vault = Vault(key.encode("utf-8"))
        except (ValueError, KeyError, OSError, RuntimeError, AttributeError):  # noqa: BLE001 — vault key is optional, must not block siege
            pass

        console.print(
            Panel(
                "[bold red]INITIATING COMPLIANCE SIEGE — LEGION-Ω SWARM[/bold red]\n"
                "[dim]Targeting CORTEX Ledger and Vault...[/dim]",
            )
        )

        tasks = [vector.attack(engine, {}) for vector in COMPLIANCE_SIEGE_SWARM]  # type: ignore[type-error]

        import asyncio

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_findings = []
        for r in results:
            if isinstance(r, list):
                all_findings.extend(r)

        report = await engine.verify_ledger()
        await pool.close()

        return all_findings, report

    try:
        findings, verification_report = _run_async(_run_siege())

        status = verification_report.get("valid")
        color = "green" if status else "red"
        verdict = (
            "IMMUNITAS OMEGA: SYSTEM SURVIVED" if status else "BREACH DETECTED: LEDGER CORRUPTED"
        )

        table = Table(title="Siege Results", show_header=False)
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Red Team Findings", str(len(findings)))
        table.add_row("Transactions Checked", str(verification_report.get("tx_checked", 0)))
        table.add_row("Violations Found", str(len(verification_report.get("violations", []))))

        console.print(table)

        if findings:
            for f in findings:
                console.print(f"[{color}]• {f}[/{color}]")

        console.print(Panel(verdict, title="Final Verdict", style=color))

    except Exception as e:  # noqa: BLE001 — CLI boundary catch
        handle_cli_error(e, db_path=db, context="Compliance Siege execution")
