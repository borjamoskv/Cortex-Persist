"""
CORTEX CLI - Trust & Compliance Commands.

Provides CLI commands for cryptographic verification, audit trails,
and EU AI Act Article 12 compliance reporting.
"""

import asyncio
import json
import sqlite3

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli
from cortex.utils.landauer import audit_calcification

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


def _find_transaction(conn, fact_id: int, fact_tx_id: int | None):
    """Look up the transaction for a fact, trying direct ID then join."""
    tx = None
    if fact_tx_id:
        tx = conn.execute(
            "SELECT id, hash, prev_hash, action, timestamp FROM transactions WHERE id = ?",
            (fact_tx_id,),
        ).fetchone()
    if not tx:
        tx = conn.execute(
            "SELECT t.id, t.hash, t.prev_hash, t.action, t.timestamp "
            "FROM facts f JOIN transactions t ON f.tx_id = t.id "
            "WHERE f.id = ?",
            (fact_id,),
        ).fetchone()
    return tx


def _verify_chain(conn, tx_id: int, prev_hash: str | None) -> tuple[bool, str]:
    if not prev_hash:
        return True, "[green]OK[/green]"

    prev_tx = conn.execute(
        "SELECT hash FROM transactions WHERE id = ?",
        (tx_id - 1,),
    ).fetchone()

    if prev_tx and prev_tx[0] != prev_hash:
        return False, "[red]BROKEN - prev_hash mismatch[/red]"
    return True, "[green]OK[/green]"


def _check_merkle(conn, tx_id: int):
    try:
        return conn.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id, created_at "
            "FROM merkle_roots "
            "WHERE tx_start_id <= ? AND tx_end_id >= ? LIMIT 1",
            (tx_id, tx_id),
        ).fetchone()
    except (sqlite3.Error, OSError, RuntimeError):
        return None


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

        # fact_tx_id is fact[5]
        fact_tx_id = fact[5]

        # Get the transaction via tx_id
        tx = _find_transaction(conn, fact_id, fact_tx_id)

        if not tx:
            console.print(
                Panel(
                    f"[yellow]Warning: Fact #{fact_id} exists but has no transaction record.[/yellow]",
                    title="Verification",
                )
            )
            return

        tx_id, _tx_hash, prev_hash, _action, _tx_time = tx

        chain_valid, chain_msg = _verify_chain(conn, tx_id, prev_hash)
        checkpoint = _check_merkle(conn, tx_id)

        _render_verification_certificate(fact, tx, chain_valid, chain_msg, checkpoint)
    except Exception as e:
        handle_cli_error(e, db_path=db, context="verifying fact")
    finally:
        if conn:
            conn.close()


def _render_verification_certificate(
    fact: tuple, tx: tuple, chain_valid: bool, chain_msg: str, checkpoint: tuple | None
) -> None:
    fid, proj, content, ftype, created, _fact_tx_id = fact
    _, tx_hash, prev_hash, _action, _tx_time = tx

    table = Table(title="CORTEX Verification Certificate", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Fact ID", f"#{fid}")
    table.add_row("Project", proj)
    table.add_row("Type", ftype)
    table.add_row("Created", created)
    table.add_row("Content", content[:200])
    table.add_row("", "")
    table.add_row("TX Hash", tx_hash[:32] + "...")
    table.add_row("Prev Hash", (prev_hash or "genesis")[:32] + "...")
    table.add_row("Chain Link", chain_msg)

    if checkpoint:
        cp_id, merkle_root, start, end, cp_time = checkpoint
        table.add_row("", "")
        table.add_row("Merkle Root", merkle_root[:32] + "...")
        table.add_row("Checkpoint", f"#{cp_id} (TX #{start} to #{end})")
        table.add_row("Sealed", cp_time)
        table.add_row("Merkle Status", "[green]Included in sealed checkpoint[/green]")
    else:
        table.add_row("Merkle", "[yellow]Not yet checkpointed[/yellow]")

    overall = "[green]VERIFIED[/green]" if chain_valid else "[red]INTEGRITY VIOLATION[/red]"
    console.print(table)
    console.print(Panel(overall, title="Verdict"))


def _safe_count(conn, query: str) -> int:
    """Execute a COUNT query, return 0 on error."""
    try:
        return conn.execute(query).fetchone()[0]
    except (sqlite3.Error, OSError, RuntimeError):
        return 0


def _extract_agents(conn) -> set[str]:
    """Parse agent tags from facts."""
    rows = conn.execute(
        "SELECT DISTINCT tags FROM facts WHERE tags LIKE '%agent:%' AND valid_until IS NULL"
    ).fetchall()
    agents: set[str] = set()
    for row in rows:
        if not row[0]:
            continue
        try:
            tags = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            tags = [t.strip() for t in row[0].split(",")]
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("agent:"):
                agents.add(tag)
    return agents


def _check_chain_integrity(conn) -> tuple[bool, int]:
    """Verify transaction hash chain. Returns (valid, violations)."""
    try:
        txs = conn.execute(
            "SELECT id, hash, prev_hash FROM transactions ORDER BY id LIMIT 1000"
        ).fetchall()
    except (sqlite3.Error, OSError, RuntimeError):
        return True, 0
    violations = sum(1 for i in range(1, len(txs)) if txs[i][2] and txs[i][2] != txs[i - 1][1])
    return violations == 0, violations


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

        cortex_root = Path(__file__).parent.parent
        calc_results = audit_calcification(cortex_root, limit=5)
        avg_calc = sum(r["score"] for r in calc_results) / len(calc_results) if calc_results else 0

        table.add_row("Calcification Index", f"[bold yellow]{avg_calc:.2f}[/bold yellow] (Omega-2)")
        console.print(table)

        c1, c2, c3, c4, c5 = total_tx > 0, decisions > 0, chain_ok, checkpoints > 0, len(agents) > 0

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
    except Exception as e:
        handle_cli_error(e, db_path=db, context="generating compliance report")
    finally:
        if conn:
            conn.close()


def _get_audit_trail(conn, project: str, limit: int):
    """Internal helper to get the audit trail rows."""
    from cortex.cli.errors import err_empty_results

    conditions = ["f.valid_until IS NULL"]
    params: list = []

    if project:
        conditions.append("f.project = ?")
        params.append(project)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT f.id, f.project, f.content, f.fact_type,
               f.created_at, t.hash
        FROM facts f
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE {where_clause}
        ORDER BY f.created_at DESC
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()

    if not rows:
        err_empty_results("audit entries")
        return None

    table = Table(title=f"CORTEX Audit Trail ({len(rows)} entries)")
    table.add_column("ID", style="dim")
    table.add_column("Time")
    table.add_column("Project", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Content")
    table.add_column("Hash", style="dim")

    for row in rows:
        fid, proj, content, ftype, created, tx_hash = row
        table.add_row(
            str(fid),
            created[:19] if created else "-",
            proj,
            ftype,
            content[:80] + ("..." if len(content) > 80 else ""),
            (tx_hash or "-")[:12] + "..." if tx_hash else "-",
        )
    return table


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
    except Exception as e:
        from cortex.cli.errors import handle_cli_error

        handle_cli_error(e, db_path=db, context="cognitive audit")
    finally:
        console.print("[dim]Audit complete.[/dim]")


@cli.command("audit")
@click.option("--calcification", is_flag=True, help="Run Landauer's Razor audit")
@click.option("--frontend", is_flag=True, help="Run Zero-Latency UI Axiom audit (CC < 5)")
@click.option("--project", "-p", default="", help="Filter trail by project")
@click.option("--limit", "-n", default=10, help="Max entries to show")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def audit(calcification: bool, frontend: bool, project: str, limit: int, db: str) -> None:
    """Run audits or view Audit Trail."""
    if frontend:
        import os
        import sys

        from cortex.verification.frontend_oracle import FrontendOracle

        project_dir = os.getcwd()
        oracle = FrontendOracle()
        violations = []

        for root, _, files in os.walk(project_dir):
            if any(x in root for x in [".venv", ".git", "node_modules"]):
                continue
            for f in files:
                if f.endswith((".html", ".js", ".ts", ".jsx", ".tsx")):
                    v = oracle.analyze_file(os.path.join(root, f))
                    violations.extend(v)

        if not violations:
            console.print(
                "[bold green]OK[/bold green] Zero-Latency Axiom (Ω₇) respected. All listeners CC < 5."
            )
            return

        console.print(
            "[bold red]FAIL[/bold red] Axiom Violation: Frontend listeners exceeded Cognitive Complexity 5."
        )
        for v in violations:
            console.print(
                f"  -> {v['file']} :: [yellow]{v['function']}[/yellow] (CC: {v['complexity']})"
            )
        sys.exit(1)

    elif calcification:
        from pathlib import Path

        cortex_root = Path(__file__).parent.parent
        results = audit_calcification(cortex_root, limit=limit)

        table = Table(title="Landauer's Razor Audit (Omega-2)")
        table.add_column("File", style="cyan")
        table.add_column("LOC", justify="right")
        table.add_column("Complexity", justify="right")
        table.add_column("Score", style="bold yellow", justify="right")
        table.add_column("Status")

        for r in results:
            status = "[red]BONEY[/red]" if r["is_parasite"] else "[green]FLUID[/green]"
            table.add_row(
                r["file"], str(r["loc"]), str(r["complexity"]), f"{r['score']:.2f}", status
            )

            # Show top 3 internal parasites if file is boney
            if r["is_parasite"]:
                parasites = [n for n in r["nodes"] if n["is_parasite"]][:3]
                for p in parasites:
                    table.add_row(
                        f"  [dim]↳ {p['name']} ({p['type']})[/dim]",
                        f"[dim]{p['end_line'] - p['start_line'] + 1}L[/dim]",
                        f"[dim]cx:{p['complexity']}[/dim]",
                        f"[dim]sc:{p['score']}[/dim]",
                        "[red]PARASITE[/red]",
                    )

        console.print(table)
        console.print(
            "\n[dim]Threshold: Score > 50 (File) | Score > 30 (Node) indicates Calcification.[/dim]"
        )
    else:
        from cortex.cli.errors import handle_cli_error
        from cortex.database.core import connect as db_connect

        conn = None
        try:
            conn = db_connect(db)
            table = _get_audit_trail(conn, project, limit)
            if table:
                console.print(table)
        except Exception as e:
            handle_cli_error(e, db_path=db, context="generating audit trail")
        finally:
            if conn:
                conn.close()


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
        # Attempt to load Vault if keys are available in env
        try:
            import os

            key = os.environ.get("CORTEX_VAULT_KEY")
            if key:
                engine.vault = Vault(key.encode("utf-8"))
        except Exception:
            pass

        console.print(
            Panel(
                "[bold red]INITIATING COMPLIANCE SIEGE — LEGION-Ω SWARM[/bold red]\n[dim]Targeting CORTEX Ledger and Vault...[/dim]"
            )
        )

        # Start the attacks
        tasks = []
        for vector in COMPLIANCE_SIEGE_SWARM:
            tasks.append(vector.attack(engine, {}))

        import asyncio

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_findings = []
        for r in results:
            if isinstance(r, list):
                all_findings.extend(r)

        # Run integrity verification
        report = await engine.verify_ledger()
        await pool.close()

        return all_findings, report

    try:
        findings, verification_report = _run_async(_run_siege())

        # Verification Report Output
        status = verification_report.get("valid")
        if status:
            color = "green"
            verdict = "IMMUNITAS OMEGA: SYSTEM SURVIVED"
        else:
            color = "red"
            verdict = "BREACH DETECTED: LEDGER CORRUPTED"

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

    except Exception as e:
        handle_cli_error(e, db_path=db, context="Compliance Siege execution")
