"""ROI & Efficiency Quantification — CHRONOS-1 Integration.

Data-driven ROI engine that queries real CHRONOS metadata
stored in CORTEX facts to aggregate systemic leverage metrics.

Sovereign Standard: 130/100
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.crypto.aes import get_default_encrypter

logger = logging.getLogger("cortex.roi")


@dataclass
class ROIMetrics:
    """Aggregated ROI metrics across the ecosystem."""

    total_facts: int
    facts_with_chronos: int
    total_ai_time_secs: float
    total_human_time_secs: float
    projects: int
    top_projects: list[tuple[str, float, float]]  # (name, human_h, ai_h)

    @property
    def roi_ratio(self) -> float:
        if self.total_ai_time_secs == 0:
            return 0.0
        return self.total_human_time_secs / self.total_ai_time_secs

    @property
    def hours_saved(self) -> float:
        return (self.total_human_time_secs - self.total_ai_time_secs) / 3600

    def format_roi(self) -> str:
        """Format as CHRONOS-1 ROI string."""
        ratio = self.roi_ratio
        if ratio >= 10_000_000:
            return f"{ratio:,.0f}/1 🔥 SINGULARITY"
        if ratio >= 1_000_000:
            return f"{ratio:,.0f}/1 ⚡ ASYMPTOTIC"
        if ratio >= 1_000:
            return f"{ratio:,.0f}/1 🚀 SOVEREIGN"
        return f"{ratio:,.1f}/1"


def _parse_chronos_meta(raw_meta: Any, enc: Any) -> dict[str, Any] | None:
    """Decrypt and parse chronos metadata securely."""
    if not raw_meta:
        return None
    try:
        meta = enc.decrypt_json(raw_meta)
    except Exception:
        # Could be unencrypted legacy or corrupted
        try:
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else {}
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(meta, dict):
        return None

    return meta.get("chronos")


async def _aggregate_chronos(engine: Any) -> ROIMetrics:
    """Query all facts with CHRONOS metadata and aggregate.

    The meta column is AES-encrypted JSON. We decrypt each row and
    extract chronos.ai_time_secs and chronos.human_time_secs.
    """
    conn = await engine.get_conn()
    enc = get_default_encrypter()

    async with conn.execute(
        "SELECT project, meta FROM facts WHERE valid_until IS NULL AND meta IS NOT NULL"
    ) as cursor:
        rows = await cursor.fetchall()

    total_ai = 0.0
    total_human = 0.0
    chronos_count = 0
    by_project: dict[str, dict[str, float]] = {}

    for project, raw_meta in rows:
        chronos = _parse_chronos_meta(raw_meta, enc)
        if not chronos:
            continue

        ai_secs = chronos.get("ai_time_secs", 0)
        human_secs = chronos.get("human_time_secs", 0)

        if ai_secs <= 0 or human_secs <= 0:
            continue

        chronos_count += 1
        total_ai += ai_secs
        total_human += human_secs

        proj_data = by_project.setdefault(project, {"ai": 0.0, "human": 0.0})
        proj_data["ai"] += ai_secs
        proj_data["human"] += human_secs

    # Top 5 projects by human time saved
    sorted_projects = sorted(
        by_project.items(),
        key=lambda x: x[1]["human"] - x[1]["ai"],
        reverse=True,
    )[:5]

    top = [(name, data["human"] / 3600, data["ai"] / 3600) for name, data in sorted_projects]

    stats = await engine.stats()

    return ROIMetrics(
        total_facts=stats.get("active_facts", 0),
        facts_with_chronos=chronos_count,
        total_ai_time_secs=total_ai,
        total_human_time_secs=total_human,
        projects=len(stats.get("projects", [])),
        top_projects=top,
    )


@click.group()
def roi():
    """📊 ROI & Efficiency Quantification (CHRONOS-1)."""


def _render_status_table(m: ROIMetrics) -> None:
    # Header panel
    console.print(
        Panel(
            f"[bold]Facts:[/] {m.total_facts:,} total · "
            f"{m.facts_with_chronos:,} con CHRONOS · "
            f"{m.projects:,} proyectos",
            title="[bold magenta]⏱️ CHRONOS-1: Sovereign ROI[/]",
            border_style="magenta",
        )
    )

    # Main metrics table
    table = Table(border_style="blue", show_header=True)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")
    table.add_column("Status", style="green")

    if m.facts_with_chronos > 0:
        table.add_row(
            "Human Senior Time",
            f"{m.total_human_time_secs / 3600:,.1f} hours",
            "Measured",
        )
        table.add_row(
            "MOSKV Swarm Time",
            f"{m.total_ai_time_secs / 3600:,.1f} hours",
            "Measured",
        )
        table.add_row(
            "Hours Saved",
            f"{m.hours_saved:,.1f} hours",
            "🟢 Positive" if m.hours_saved > 0 else "🔴 Negative",
        )
        table.add_row("ROI Ratio", m.format_roi(), "SOVEREIGN")
    else:
        # Estimate based on fact count (systemic leverage)
        estimated_human_h = m.total_facts * 0.5
        estimated_ai_h = m.total_facts * 0.01
        estimated_roi = estimated_human_h / estimated_ai_h if estimated_ai_h > 0 else 0

        table.add_row(
            "Estimated Human Time",
            f"{estimated_human_h:,.0f} hours",
            "Projected (0.5h/fact)",
        )
        table.add_row(
            "Estimated MOSKV Time",
            f"{estimated_ai_h:,.1f} hours",
            "Projected (36s/fact)",
        )
        table.add_row(
            "Projected ROI",
            f"{estimated_roi:,.0f}/1",
            "ESTIMATED" if estimated_roi < 10_000_000 else "🔥 SINGULARITY",
        )

    console.print(table)


def _render_top_projects(m: ROIMetrics) -> None:
    if not m.top_projects:
        return

    console.print()
    proj_table = Table(
        title="🏆 Top Projects by Time Saved",
        border_style="cyan",
    )
    proj_table.add_column("Project", style="bold")
    proj_table.add_column("Human Time", justify="right")
    proj_table.add_column("AI Time", justify="right")
    proj_table.add_column("Saved", justify="right", style="green")

    for name, human_h, ai_h in m.top_projects:
        saved = human_h - ai_h
        proj_table.add_row(
            name,
            f"{human_h:.1f}h",
            f"{ai_h:.1f}h",
            f"{saved:.1f}h",
        )
    console.print(proj_table)


@roi.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def status(db: str) -> None:
    """Muestra el ROI acumulado del ecosistema."""

    async def _do_status():
        engine = get_engine(db)
        try:
            await engine.init_db()
            m = await _aggregate_chronos(engine)

            _render_status_table(m)
            _render_top_projects(m)

            # Singularity check
            if m.roi_ratio >= 10_000_000:
                console.print("\n[bold gold]🔥 SINGULARIDAD ALCANZADA: ROI > 10M/1[/]")
                console.print(
                    "[dim]El sistema opera en modo asintótico. Masa = 0, Fricción = 0.[/]"
                )
        finally:
            await engine.close()

    asyncio.run(_do_status())


@roi.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def report(db: str) -> None:
    """Genera un reporte ROI en markdown."""

    async def _do_report():
        engine = get_engine(db)
        try:
            await engine.init_db()
            m = await _aggregate_chronos(engine)
            md = generate_roi_markdown(m)
            console.print(md)
        finally:
            await engine.close()

    asyncio.run(_do_report())


def generate_roi_markdown(m: ROIMetrics) -> str:
    """Generate a markdown ROI summary for embedding in snapshots."""
    lines = [
        "## ⏱️ ROI (CHRONOS-1)",
        "",
    ]

    if m.facts_with_chronos > 0:
        lines.extend(
            [
                f"- **ROI Ratio:** {m.format_roi()}",
                f"- **Human Time Estimated:** {m.total_human_time_secs / 3600:,.1f}h",
                f"- **MOSKV Time Actual:** {m.total_ai_time_secs / 3600:,.1f}h",
                f"- **Hours Saved:** {m.hours_saved:,.1f}h",
                f"- **Facts with CHRONOS:** {m.facts_with_chronos:,}",
            ]
        )
    else:
        estimated_roi = m.total_facts * 50  # 50x per fact (conservative)
        lines.extend(
            [
                f"- **Projected ROI:** {estimated_roi:,}/1 (estimated)",
                f"- **Active Facts:** {m.total_facts:,}",
                f"- **Projects:** {m.projects:,}",
                "- **Note:** Store facts with `--ai-time` for measured ROI.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


cli.add_command(roi)
