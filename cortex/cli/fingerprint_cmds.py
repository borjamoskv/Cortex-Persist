"""CLI commands: cortex fingerprint — cognitive pattern extraction."""

from __future__ import annotations

import json as json_mod

import click

from cortex.cli.common import _run_async, cli, close_engine_sync, console, get_engine
from cortex.cli.errors import handle_cli_error

__all__ = ["fingerprint", "fingerprint_extract"]


@cli.group()
def fingerprint():
    """Cognitive Fingerprint — Extract your decision-making patterns."""
    pass


def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _score_color(v: float) -> str:
    if v >= 0.65:
        return "green"
    if v >= 0.35:
        return "yellow"
    return "red"


def _arch_badge(name: str, confidence: float) -> str:
    if confidence >= 0.6:
        color = "bold cyan"
    elif confidence >= 0.4:
        color = "bold yellow"
    else:
        color = "dim white"
    label = name.replace("_", " ").upper()
    return f"[{color}]{label}[/] [dim]({confidence:.0%} confidence)[/]"


@fingerprint.command("extract")
@click.option("--project", "-p", default=None, help="Filter by project.")
@click.option("--json", "as_json", is_flag=True, help="JSON output.")
@click.option("--prompt", is_flag=True, help="Output agent prompt injection.")
@click.option("--top", default=15, help="Max domain preferences shown.", show_default=True)
def fingerprint_extract(
    project: str | None,
    as_json: bool,
    prompt: bool,
    top: int,
) -> None:
    """Extract the Cognitive Fingerprint from the CORTEX Ledger."""
    from cortex.fingerprint.extractor import FingerprintExtractor

    engine = get_engine()
    try:
        fp = _run_async(FingerprintExtractor.extract(engine, project, top_domains=top))

        # ── JSON output ───────────────────────────────────────────────
        if as_json:
            console.print_json(json_mod.dumps(fp.to_dict(), indent=2))
            return

        # ── Agent prompt injection ────────────────────────────────────
        if prompt:
            console.print(fp.to_agent_prompt())
            return

        # ── Rich TUI ─────────────────────────────────────────────────
        title = "🧬 COGNITIVE FINGERPRINT"
        if project:
            title += f"  ·  {project}"

        console.print(
            f"\n[noir.cyber]{title}[/]  "
            f"[dim]({fp.total_facts_analyzed} facts · "
            f"{fp.active_domains} domains · "
            f"{fp.fingerprint_completeness:.0%} completeness)[/]\n"
        )
        console.print(f"  Archetype: {_arch_badge(fp.archetype, fp.archetype_confidence)}\n")

        # Pattern vector table
        from rich.table import Table

        p_table = Table(show_header=True, header_style="bold cyan", box=None)
        p_table.add_column("Dimension", style="bold white", min_width=20)
        p_table.add_column("Symbol", justify="center", width=6)
        p_table.add_column("Value", justify="right", width=7)
        p_table.add_column("Bar", min_width=22)

        dimensions = [
            ("Risk Tolerance",   "τ", fp.pattern.risk_tolerance),
            ("Caution Index",    "ψ", fp.pattern.caution_index),
            ("Synthesis Drive",  "σ", fp.pattern.synthesis_drive),
            ("Session Density",  "ρ", fp.pattern.session_density),
            ("Recency Bias",     "β", fp.pattern.recency_bias),
            ("Breadth",         "β̃", fp.pattern.breadth),
            ("Depth",            "δ", fp.pattern.depth_preference),
        ]
        for label, sym, val in dimensions:
            color = _score_color(val)
            p_table.add_row(
                label, sym,
                f"[{color}]{val:.0%}[/]",
                f"[{color}]{_bar(val)}[/]",
            )
        console.print(p_table)

        # Top domains
        if fp.domain_preferences:
            console.print("\n[bold white]Top Domains[/]")
            d_table = Table(show_header=True, header_style="dim", box=None)
            d_table.add_column("Project", style="white")
            d_table.add_column("Type", style="dim")
            d_table.add_column("Count", justify="right")
            d_table.add_column("/week", justify="right")
            d_table.add_column("Conf", justify="right")
            d_table.add_column("Days ago", justify="right")

            for d in fp.domain_preferences[:10]:
                conf_color = _score_color(d.avg_confidence_weight)
                d_table.add_row(
                    d.project,
                    d.fact_type,
                    str(d.count),
                    f"{d.store_frequency_per_week:.1f}",
                    f"[{conf_color}]{d.avg_confidence_weight:.0%}[/]",
                    f"{d.recency_days:.0f}",
                )
            console.print(d_table)

        console.print(
            "\n[dim]Run with --prompt to get agent injection · "
            "--json for machine output[/]"
        )

    except (OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, context="fingerprint extract")
    finally:
        close_engine_sync(engine)
