"""CORTEX CLI — Tips Commands.

Surface contextual tips from the TIPS engine.
Designed to display during agent thinking pauses.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.tips import Tip, TipCategory, TipsEngine


def _get_tips_engine(db: str, lang: str = "en") -> TipsEngine:
    """Create a TipsEngine with optional CORTEX backend."""
    try:
        engine = get_engine(db)
        return TipsEngine(engine, include_dynamic=True, lang=lang)
    except (RuntimeError, OSError, ValueError):
        return TipsEngine(include_dynamic=False, lang=lang)


# ─── Tips Group ──────────────────────────────────────────────────────


@cli.group(invoke_without_command=True)
@click.option("--db", default=DEFAULT_DB, help="Database path.")
@click.option(
    "--category",
    "-c",
    type=click.Choice([c.value for c in TipCategory], case_sensitive=False),
    help="Filter by category.",
)
@click.option("--project", "-p", help="Filter by project scope.")
@click.option("--count", "-n", default=1, type=int, help="Number of tips to show.")
@click.option("--lang", "-l", help="Language code (en, es, eu). Defaults to auto-detect.")
@click.pass_context
def tips(
    ctx: click.Context,
    db: str,
    category: str | None,
    project: str | None,
    count: int,
    lang: str | None,
) -> None:
    """💡 TIPS — Contextual tips and insights from CORTEX."""
    # Simple auto-detect: if not provided, check OS/env or default to ES for this session
    # but for a general tool, we usually default to EN unless specified.
    # However, since the user ASKED for Spanish, I'll default to ES if lang is None
    # but a better way is to keep EN as system default and let user override.
    # Actually, I'll check Lang enum or default to 'en'
    final_lang = lang or "es"  # Prioritize Spanish as requested by the user

    if ctx.invoked_subcommand is not None:
        ctx.ensure_object(dict)
        ctx.obj["db"] = db
        ctx.obj["lang"] = final_lang
        return

    tips_engine = _get_tips_engine(db, lang=final_lang)

    if category:
        results = tips_engine.for_category(category, limit=count)
    elif project:
        results = tips_engine.for_project(project, limit=count)
    else:
        results = [tips_engine.random() for _ in range(count)]

    if not results:
        console.print("[dim]No tips found for the given filters.[/dim]")
        return

    for tip in results:
        _render_tip(tip)


# ─── Subcommands ─────────────────────────────────────────────────────


@tips.command(name="list")
@click.pass_context
def tips_list(ctx: click.Context) -> None:
    """List all tip categories and counts."""
    db = ctx.obj["db"]
    lang = ctx.obj["lang"]
    tips_engine = _get_tips_engine(db, lang=lang)

    table = Table(
        title=f"💡 TIPS Categories ({lang})",
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Category", style="bold green")
    table.add_column("Count", justify="right", style="cyan")

    all_tips = tips_engine.all_tips()
    for cat in TipCategory:
        cat_count = sum(1 for t in all_tips if t.category == cat)
        if cat_count > 0:
            table.add_row(cat.value, str(cat_count))

    table.add_section()
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{len(all_tips)}[/bold]")
    console.print(table)


@tips.command(name="all")
@click.option(
    "--category",
    "-c",
    type=click.Choice([c.value for c in TipCategory], case_sensitive=False),
    help="Filter by category.",
)
@click.pass_context
def tips_all(ctx: click.Context, category: str | None) -> None:
    """Show all available tips."""
    db = ctx.obj["db"]
    lang = ctx.obj["lang"]
    tips_engine = _get_tips_engine(db, lang=lang)

    if category:
        all_tips = tips_engine.for_category(category, limit=100)
    else:
        all_tips = tips_engine.all_tips()

    if not all_tips:
        console.print("[dim]No tips available.[/dim]")
        return

    table = Table(
        title=f"💡 All TIPS ({lang})",
        title_style="bold cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Category", style="bold green", width=14)
    table.add_column("Tip", ratio=1)
    table.add_column("Source", style="dim", width=8)

    for idx, tip in enumerate(all_tips, 1):
        table.add_row(
            str(idx),
            tip.category.value,
            tip.content,
            tip.source,
        )

    console.print(table)


@tips.command(name="random")
@click.option("--count", "-n", default=3, type=int, help="Number of random tips.")
@click.pass_context
def tips_random(ctx: click.Context, count: int) -> None:
    """Show random tips (great for thinking pauses)."""
    db = ctx.obj["db"]
    lang = ctx.obj["lang"]
    tips_engine = _get_tips_engine(db, lang=lang)

    console.print()
    for _ in range(count):
        tip = tips_engine.random()
        _render_tip(tip)
    console.print()


# ─── Rendering ───────────────────────────────────────────────────────


def _render_tip(tip: Tip) -> None:
    """Render a single tip as a Rich panel."""
    console.print(
        Panel(
            f"[white]{tip.content}[/white]",
            title=f"[bold cyan]💡 {tip.category.value.upper()}[/bold cyan]",
            subtitle=f"[dim]{tip.source} • {tip.lang}[/dim]",
            border_style="bright_green",
            padding=(0, 2),
        )
    )
