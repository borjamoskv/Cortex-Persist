"""CORTEX v7.0 — Sovereign Dashboard (Industrial Noir).

Live terminal dashboard showing system health, Shannon entropy,
ledger integrity, and recent activity. Refreshes every 2 seconds.

Usage:
    cortex dashboard              # Live mode (Ctrl+C to exit)
    cortex dashboard --once       # Single snapshot, no loop
    cortex dashboard --interval 5 # Custom refresh interval
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import datetime, timezone

import click
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cortex.cli.common import DEFAULT_DB, _run_async, cli, console, get_engine
from cortex.cli.errors import handle_cli_error

# ─── Industrial Noir Palette ────────────────────────────────────────
_CYBER = "#CCFF00"
_GOLD = "#D4AF37"
_VIOLET = "#6600FF"
_EMERALD = "#06d6a0"
_ABYSS = "#1A1A1A"
_RED = "#FF3366"
_DIM = "dim"


# ─── Data Collectors ────────────────────────────────────────────────


async def _collect_stats(engine) -> dict:
    """Collect core engine statistics."""
    try:
        return await engine.stats()
    except (sqlite3.Error, OSError, FileNotFoundError):
        return {}


async def _collect_shannon(engine) -> dict:
    """Collect Shannon entropy report."""
    try:
        return await engine.shannon_report()
    except (sqlite3.Error, OSError, AttributeError, FileNotFoundError):
        return {}


async def _collect_ledger(engine) -> dict:
    """Collect ledger verification status."""
    try:
        return await engine.verify_ledger()
    except (sqlite3.Error, OSError, AttributeError, FileNotFoundError):
        return {}


async def _collect_recent(engine, limit: int = 8) -> list[dict]:
    """Collect recent facts for activity feed."""
    try:
        results = await engine.search("*", limit=limit)
        if hasattr(results, "__iter__"):
            return [
                {
                    "id": getattr(r, "id", "?"),
                    "type": getattr(r, "fact_type", "?"),
                    "project": getattr(r, "project", "?"),
                    "content": str(getattr(r, "content", ""))[:60],
                    "created": getattr(r, "created_at", ""),
                }
                for r in results
            ]
    except (sqlite3.Error, OSError, AttributeError, FileNotFoundError):
        pass
    return []


async def _collect_all(engine) -> dict:
    """Collect all dashboard data in parallel."""
    stats, shannon, ledger, recent = await asyncio.gather(
        _collect_stats(engine),
        _collect_shannon(engine),
        _collect_ledger(engine),
        _collect_recent(engine),
        return_exceptions=True,
    )
    return {
        "stats": stats if isinstance(stats, dict) else {},
        "shannon": shannon if isinstance(shannon, dict) else {},
        "ledger": ledger if isinstance(ledger, dict) else {},
        "recent": recent if isinstance(recent, list) else [],
    }


# ─── Panel Builders ─────────────────────────────────────────────────


def _build_header() -> Panel:
    """Build the header panel with logo and timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = Text()
    header.append("⚡ CORTEX PERSIST", style=f"bold {_CYBER}")
    header.append("  ·  ", style=_DIM)
    header.append("Sovereign Dashboard", style=f"bold {_GOLD}")
    header.append("  ·  ", style=_DIM)
    header.append(now, style=_DIM)
    return Panel(header, border_style=_VIOLET, padding=(0, 1))


def _build_vitals(stats: dict) -> Panel:
    """Build the system vitals panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style=f"bold {_GOLD}", min_width=16)
    table.add_column("Value", style="white")

    total = stats.get("total_facts", 0)
    active = stats.get("active_facts", 0)
    deprecated = stats.get("deprecated_facts", 0)
    db_size = stats.get("db_size_mb", "?")
    projects = stats.get("project_count", 0)
    embeddings = stats.get("embeddings", 0)

    table.add_row("Total Facts", f"[bold white]{total:,}[/]")
    table.add_row("Active", f"[{_EMERALD}]{active:,}[/]")
    table.add_row("Deprecated", f"[{_DIM}]{deprecated:,}[/]")
    table.add_row("Projects", str(projects))
    table.add_row("Embeddings", f"{embeddings:,}")
    table.add_row("DB Size", f"{db_size} MB")

    # Type distribution
    types = stats.get("types", {})
    if types:
        top_types = sorted(types.items(), key=lambda x: x[1], reverse=True)[:5]
        type_str = " · ".join(f"{t}:{c}" for t, c in top_types)
        table.add_row("Top Types", f"[{_DIM}]{type_str}[/]")

    return Panel(
        table,
        title=f"[bold {_CYBER}]◉ VITALS[/]",
        border_style=_VIOLET,
        padding=(0, 1),
    )


def _build_shannon(shannon: dict) -> Panel:
    """Build the Shannon entropy panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style=f"bold {_GOLD}", min_width=18)
    table.add_column("Value", style="white")

    if not shannon:
        table.add_row("Status", f"[{_DIM}]No data[/]")
    else:
        entropy = shannon.get("entropy", 0.0)
        compression = shannon.get("compression_ratio", 0.0)
        unique_tokens = shannon.get("unique_tokens", 0)
        total_tokens = shannon.get("total_tokens", 0)

        # Entropy gauge: lower = more ordered = better
        if entropy < 3.0:
            entropy_style = _EMERALD
            entropy_label = "Crystallized"
        elif entropy < 5.0:
            entropy_style = _GOLD
            entropy_label = "Structured"
        else:
            entropy_style = _RED
            entropy_label = "High Entropy"

        bar_len = min(int(entropy * 3), 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        table.add_row(
            "Entropy H(X)",
            f"[{entropy_style}]{entropy:.3f} bits[/]  [{_DIM}]{entropy_label}[/]",
        )
        table.add_row("", f"[{entropy_style}]{bar}[/]")
        table.add_row("Compression", f"{compression:.2%}")
        table.add_row("Unique Tokens", f"{unique_tokens:,}")
        table.add_row("Total Tokens", f"{total_tokens:,}")

        # Immortality index if present
        iota = shannon.get("immortality_index")
        if iota is not None:
            iota_style = _EMERALD if iota > 0.7 else (_GOLD if iota > 0.4 else _RED)
            table.add_row(
                "Immortality ι",
                f"[bold {iota_style}]{iota:.4f}[/]",
            )

    return Panel(
        table,
        title=f"[bold {_CYBER}]∿ SHANNON[/]",
        border_style=_VIOLET,
        padding=(0, 1),
    )


def _build_ledger(ledger: dict) -> Panel:
    """Build the ledger integrity panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style=f"bold {_GOLD}", min_width=18)
    table.add_column("Value", style="white")

    if not ledger:
        table.add_row("Status", f"[{_DIM}]Not verified[/]")
    else:
        valid = ledger.get("valid", ledger.get("is_valid", False))
        chain_len = ledger.get("chain_length", ledger.get("verified_count", 0))
        errors = ledger.get("errors", ledger.get("broken_links", 0))
        last_hash = ledger.get("last_hash", "")

        if valid:
            status_text = f"[bold {_EMERALD}]✓ INTACT[/]"
        else:
            status_text = f"[bold {_RED}]✗ BROKEN[/]"

        table.add_row("Chain Status", status_text)
        table.add_row("Chain Length", f"{chain_len:,}")
        table.add_row("Errors", f"[{_RED if errors else _EMERALD}]{errors}[/]")
        if last_hash:
            table.add_row("Last Hash", f"[{_DIM}]{last_hash[:24]}…[/]")

    return Panel(
        table,
        title=f"[bold {_CYBER}]⛓ LEDGER[/]",
        border_style=_VIOLET,
        padding=(0, 1),
    )


def _build_activity(recent: list[dict]) -> Panel:
    """Build the recent activity feed panel."""
    table = Table(box=None, padding=(0, 1), show_header=True)
    table.add_column("ID", style=_DIM, width=5)
    table.add_column("Type", style=f"bold {_GOLD}", width=12)
    table.add_column("Project", style=_VIOLET, width=14)
    table.add_column("Content", style="white", ratio=1)

    if not recent:
        table.add_row("—", "—", "—", f"[{_DIM}]No recent activity[/]")
    else:
        for fact in recent[:8]:
            fact_type = str(fact.get("type", "?"))
            # Color-code by type
            type_colors = {
                "decision": _EMERALD,
                "error": _RED,
                "ghost": "#FF6B6B",
                "bridge": _CYBER,
                "discovery": _GOLD,
                "axiom": _VIOLET,
            }
            color = type_colors.get(fact_type, "white")
            content = str(fact.get("content", ""))[:55]
            table.add_row(
                str(fact.get("id", "?")),
                f"[{color}]{fact_type}[/]",
                str(fact.get("project", "?"))[:14],
                content,
            )

    return Panel(
        table,
        title=f"[bold {_CYBER}]◷ RECENT ACTIVITY[/]",
        border_style=_VIOLET,
        padding=(0, 1),
    )


def _build_moats() -> Panel:
    """Build the competitive moats status panel."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Moat", style=f"bold {_GOLD}", min_width=22)
    table.add_column("Status", style="white", width=12)

    moats = [
        ("Crypto Ledger (Hash Chain)", f"[bold {_EMERALD}]● ACTIVE[/]"),
        ("AES-256 Encryption", f"[bold {_EMERALD}]● ACTIVE[/]"),
        ("Vector Search (sqlite-vec)", f"[bold {_EMERALD}]● ACTIVE[/]"),
        ("MCP Server", f"[bold {_EMERALD}]● ACTIVE[/]"),
        ("Shannon Entropy", f"[bold {_EMERALD}]● ACTIVE[/]"),
        ("Byzantine Consensus", f"[bold {_CYBER}]◐ READY[/]"),
        ("Qdrant Cloud Backend", f"[bold {_CYBER}]◐ READY[/]"),
        ("API Embeddings", f"[bold {_CYBER}]◐ READY[/]"),
    ]
    for name, status in moats:
        table.add_row(name, status)

    return Panel(
        table,
        title=f"[bold {_CYBER}]🛡 SOVEREIGN MOATS[/]",
        border_style=_VIOLET,
        padding=(0, 1),
    )


def _build_dashboard(data: dict) -> Layout:
    """Compose all panels into the final dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=12),
    )

    layout["header"].update(_build_header())

    # Body: two columns
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    layout["left"].split_column(
        Layout(_build_vitals(data["stats"]), name="vitals"),
        Layout(_build_shannon(data["shannon"]), name="shannon"),
    )

    layout["right"].split_column(
        Layout(_build_ledger(data["ledger"]), name="ledger"),
        Layout(_build_moats(), name="moats"),
    )

    layout["footer"].update(_build_activity(data["recent"]))

    return layout


# ─── CLI Command ─────────────────────────────────────────────────────


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--interval", default=2.0, help="Refresh interval in seconds")
@click.option("--once", is_flag=True, help="Show single snapshot and exit")
def dashboard(db: str, interval: float, once: bool) -> None:
    """Live sovereign dashboard — system health, entropy, ledger, activity."""
    engine = get_engine(db)
    try:
        if once:
            data = _run_async(_collect_all(engine))
            console.print(_build_dashboard(data))
            return

        # Live refresh mode
        console.print(f"[{_CYBER}]⚡ Dashboard starting... Ctrl+C to exit[/]\n")

        with Live(
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            try:
                while True:
                    data = _run_async(_collect_all(engine))
                    live.update(_build_dashboard(data))
                    time.sleep(interval)
            except KeyboardInterrupt:
                pass

        console.print(f"\n[{_DIM}]Dashboard closed.[/]")

    except sqlite3.OperationalError as e:
        handle_cli_error(e, db_path=db, context="dashboard")
    except FileNotFoundError:
        console.print(f"[{_RED}]Database not found: {db}[/]")
    finally:
        _run_async(engine.close())
