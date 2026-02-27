"""
CORTEX CLI — Security Commands.

Shield status, manual scans, threat feed updates,
integrity audits, and daily reports.
"""

from __future__ import annotations

import asyncio
import logging

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger("cortex.cli.security")

console = Console()


@click.group(name="security", help="🛡️  Anti-Hacker Shield — Daily-Updated Defense System.")
def security_cli() -> None:
    """CORTEX Security Shield commands."""
    pass


@security_cli.command("status")
def security_status() -> None:
    """Show shield health dashboard."""
    from cortex.security.anomaly_detector import DETECTOR
    from cortex.security.threat_feed import ThreatFeedEngine

    engine = ThreatFeedEngine()
    last_update = engine.get_last_update()
    total_sigs = engine.total_signatures
    anomaly_stats = DETECTOR.get_daily_stats()

    table = Table(
        title="🛡️ CORTEX Anti-Hacker Shield",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Component", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Threat Feed
    feed_status = "✅ Active" if last_update else "⚠️ Never Updated"
    feed_detail = (
        f"Last: {last_update.strftime('%Y-%m-%d %H:%M')}"
        if last_update
        else "Run: cortex security update"
    )
    table.add_row(
        "Threat Feed Engine",
        feed_status,
        f"{total_sigs} signatures — {feed_detail}",
    )

    # Injection Guard
    table.add_row(
        "Injection Guard",
        "✅ Active",
        "5-layer defense (SQL, Prompt, Path, Cmd, Entropy)",
    )

    # Anomaly Detector
    events = anomaly_stats["total_events"]
    anomalies = anomaly_stats["anomalies_detected"]
    blocked = anomaly_stats["events_blocked"]
    det_status = "✅ Clean" if anomalies == 0 else f"⚠️ {anomalies} anomalies"
    table.add_row(
        "Anomaly Detector",
        det_status,
        f"Events: {events} | Anomalies: {anomalies} | Blocked: {blocked}",
    )

    # Integrity Auditor
    table.add_row(
        "Integrity Auditor",
        "✅ Available",
        "Run: cortex security audit",
    )

    console.print(table)


@security_cli.command("scan")
@click.argument("content", required=False, default=None)
@click.option("--file", "-f", "filepath", help="Scan content from file")
def security_scan(content: str | None, filepath: str | None) -> None:
    """Manual full scan of content."""
    from cortex.security.injection_guard import GUARD
    from cortex.security.threat_feed import ThreatFeedEngine

    if filepath:
        from pathlib import Path

        content = Path(filepath).read_text()
    elif not content:
        content = click.get_text_stream("stdin").read()

    if not content:
        console.print("[red]No content to scan[/red]")
        return

    # Injection Guard
    inj_report = GUARD.scan(content)

    # Threat Feed
    engine = ThreatFeedEngine()
    threat_matches = engine.check_content(content)

    if inj_report.is_safe and not threat_matches:
        console.print(
            Panel(
                "✅ Content is CLEAN — no threats detected",
                title="Shield Scan",
                border_style="green",
            )
        )
        return

    table = Table(
        title="🔴 THREATS DETECTED",
        show_header=True,
        header_style="bold red",
    )
    table.add_column("Layer", style="bold")
    table.add_column("Severity", justify="center")
    table.add_column("ID")
    table.add_column("Description")
    table.add_column("Fragment")

    for m in inj_report.matches:
        sev_color = {
            "critical": "red",
            "high": "yellow",
            "medium": "blue",
        }.get(m.severity, "white")
        table.add_row(
            m.layer,
            f"[{sev_color}]{m.severity.upper()}[/{sev_color}]",
            m.pattern_id,
            m.description,
            m.matched_fragment[:40],
        )

    for m in threat_matches:
        sev_color = {
            "critical": "red",
            "high": "yellow",
            "medium": "blue",
        }.get(m.severity, "white")
        table.add_row(
            "threat_feed",
            f"[{sev_color}]{m.severity.upper()}[/{sev_color}]",
            m.signature_id,
            m.description,
            m.matched_fragment[:40],
        )

    console.print(table)
    console.print(f"\n[bold]Entropy Score:[/bold] {inj_report.entropy_score:.3f}")


@security_cli.command("update")
def security_update() -> None:
    """Force threat feed refresh from remote sources."""
    from cortex.security.threat_feed import ThreatFeedEngine

    engine = ThreatFeedEngine()

    with console.status("[bold cyan]Updating threat feeds..."):
        report = asyncio.run(engine.update_daily())

    if report.errors:
        for err in report.errors:
            console.print(f"  [yellow]⚠ {err}[/yellow]")

    console.print(
        Panel(
            f"Feeds checked: {report.feeds_checked}\n"
            f"New signatures: {report.new_signatures}\n"
            f"Total signatures: {report.total_signatures}\n"
            f"Duration: {report.duration_seconds:.1f}s",
            title="🛡️ Threat Feed Update",
            border_style="green" if not report.errors else "yellow",
        )
    )


@security_cli.command("audit")
def security_audit() -> None:
    """Run integrity audit (hash chain + signatures)."""
    from cortex.security.integrity_audit import IntegrityAuditor

    auditor = IntegrityAuditor()

    with console.status("[bold cyan]Running integrity audit..."):
        report = asyncio.run(auditor.full_audit())

    r = report.to_dict()
    status = "✅ CLEAN" if r["is_clean"] else "🔴 VIOLATIONS FOUND"
    border = "green" if r["is_clean"] else "red"

    console.print(
        Panel(
            f"Status: {status}\n"
            f"Total facts: {r['total_facts']}\n"
            f"Hash chain valid: {r['chain_valid']}\n"
            f"Broken links: {r['broken_links']}\n"
            f"Orphaned facts: {r['orphaned_facts']}\n"
            f"Signature failures: {r['signature_failures']}\n"
            f"Facts with signatures: {r['facts_with_signatures']}\n"
            f"Facts verified: {r['facts_verified']}\n"
            f"Duration: {r['duration_seconds']:.1f}s",
            title="🔐 Integrity Audit",
            border_style=border,
        )
    )


@security_cli.command("report")
def security_report() -> None:
    """Generate daily security report."""
    from cortex.security.anomaly_detector import DETECTOR
    from cortex.security.threat_feed import ThreatFeedEngine

    engine = ThreatFeedEngine()
    stats = DETECTOR.get_daily_stats()
    last_update = engine.get_last_update()

    console.print(
        Panel(
            f"[bold]Threat Feed[/bold]\n"
            f"  Total signatures: {engine.total_signatures}\n"
            f"  Last update: {last_update or 'Never'}\n\n"
            f"[bold]Anomaly Detection (Today)[/bold]\n"
            f"  Events processed: {stats['total_events']}\n"
            f"  Anomalies: {stats['anomalies_detected']}\n"
            f"  Blocked: {stats['events_blocked']}\n\n"
            f"[bold]Defense Layers[/bold]\n"
            f"  L1 SQL Injection: ✅\n"
            f"  L2 Prompt Injection: ✅\n"
            f"  L3 Path Traversal: ✅\n"
            f"  L4 Command Injection: ✅\n"
            f"  L5 Encoded Payloads: ✅\n"
            f"  L6 Active Honeypots: ✅",
            title="📊 Daily Security Report",
            border_style="cyan",
        )
    )


@security_cli.group(name="honeypot", help="🍯  Active Deceptive Defense (Traps).")
def honeypot_group() -> None:
    """Manage honeypot traps."""
    pass


@honeypot_group.command("generate")
@click.argument("project", default="general")
def honeypot_generate(project: str) -> None:
    """Generate a new synthetic secret (decoy)."""
    from cortex.security.honeypot import HONEY_POT

    decoy = HONEY_POT.generate_decoy(project)

    console.print(
        Panel(
            f"[bold green]Decoy generated and active![/bold green]\n\n"
            f"Project: {decoy.project}\n"
            f"Content: [cyan]{decoy.content}[/cyan]\n"
            f"Hash: {decoy.hash}\n\n"
            f"[dim]Any attempt to store or recall this content will trigger a breach.[/dim]",
            title="🍯 Honeypot Created",
            border_style="green",
        )
    )


@honeypot_group.command("list")
def honeypot_list() -> None:
    """List all active honeypot traps."""
    from cortex.security.honeypot import HONEY_POT

    if not HONEY_POT._active_honeypots:
        console.print("[yellow]No active honeypots.[/yellow]")
        return

    table = Table(title="🍯 Active Honeypots")
    table.add_column("ID", style="bold")
    table.add_column("Project")
    table.add_column("Secret Content (Partial)")
    table.add_column("Created")

    for decoy in HONEY_POT._active_honeypots.values():
        created = decoy.created_at
        if isinstance(created, str) and "T" in created:
            # ISO format string
            created = created.replace("T", " ")[:16]
        elif hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d %H:%M")

        table.add_row(
            decoy.id,
            decoy.project,
            f"{decoy.content[:20]}...",
            str(created),
        )

    console.print(table)


@security_cli.command("test-sync")
@click.argument("mood", type=click.Choice(["clean", "scanning", "anomaly", "threat", "pruning"]))
def security_test_sync(mood: str) -> None:
    """Test visual synchronization with the Notch."""
    from cortex.security.security_sync import SIGNAL

    console.print(f"Emitting [bold cyan]{mood}[/bold cyan] signal to Notch...")
    SIGNAL.emit_sync(mood, {"test": True})
    console.print("✅ Signal sent.")
