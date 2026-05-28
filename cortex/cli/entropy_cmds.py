"""CLI commands: entropy install-hook, scan, report, shannon."""

from __future__ import annotations

import json as json_mod
import shutil
from pathlib import Path
from typing import Any

import click

from cortex.cli.common import _run_async, cli, close_engine_sync, console, get_engine
from cortex.cli.errors import err_empty_results, err_platform, handle_cli_error

__all__ = [
    "entropy",
    "entropy_immortality",
    "entropy_install_hook",
    "entropy_report",
    "entropy_shannon",
]


@cli.group()
def entropy():
    """ENTROPY-0 v1.0 — El Guardián de la Deuda Técnica."""
    pass


@entropy.command("install-hook")
def entropy_install_hook():
    """Instala ENTROPY-0 como hook de pre-commit en el repositorio actual."""
    try:
        git_dir = Path.cwd() / ".git"
        if not git_dir.exists():
            err_platform("No se encontró un repositorio Git en este directorio.")
            return

        hook_dir = git_dir / "hooks"
        hook_dir.mkdir(exist_ok=True)

        # Ruta del archivo pre-commit
        pre_commit_file = hook_dir / "pre-commit"

        # Ruta del script origen
        import cortex

        source_script = Path(cortex.__file__).parent / "hooks" / "zero_debt.py"

        if not source_script.exists():
            err_platform(f"No se encontró el script zero_debt.py en {source_script}")
            return

        shutil.copy2(source_script, pre_commit_file)
        pre_commit_file.chmod(0o755)

        console.print("[bold green]✅ ENTROPY-0 instalado exitosamente en .git/hooks/pre-commit[/]")
        console.print(
            "[dim]A partir de ahora, ningún commit pasará si la puntuación MEJORAlo es < 90.[/]"
        )
    except (OSError, ValueError, RuntimeError, ImportError) as e:
        handle_cli_error(e, context="installing entropy hook")


@entropy.command("report")
def entropy_report():
    """Genera un reporte del estado de inmunidad del proyecto."""
    console.print("[bold cyan]🔍 Analizando inmunidad del ecosistema...[/]")
    from cortex.extensions.daemon.core import MoskvDaemon

    try:
        status_dict = MoskvDaemon.load_status()
        if not status_dict:
            err_empty_results("daemon status", suggestion="Ensure MoskvDaemon is running.")
            return

        alerts = status_dict.get("entropy_alerts", [])
        if not alerts:
            console.print("[bold green]✅ Estado: ENTROPY-0 activo. Cero deuda técnica en vivo.[/]")
        else:
            console.print(
                f"[bold red]⚠️ Alerta: Se detectaron {len(alerts)} "
                "proyectos con entropía crítica:[/]"
            )
            for alert in alerts:
                console.print(
                    f"  - [bold]{alert['project']}[/]: {alert['message']} "
                    f"(Score: {alert['complexity_score']}/100)"
                )

        # Sugerencias si el monitor está deshabilitado
        if "entropy_alerts" not in status_dict:
            console.print(
                "[dim italic]Nota: El monitor de entropía "
                "podría no estar habilitado en la configuración.[/]"
            )
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        handle_cli_error(e, context="generating entropy report")


def _bar(value: float, width: int = 20) -> str:
    """Render a normalized [0,1] value as a Unicode bar."""
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _health_badge(score: int) -> str:
    """Color-coded health badge."""
    if score >= 75:
        return f"[bold green]🟢 {score}/100[/]"
    if score >= 45:
        return f"[bold yellow]🟡 {score}/100[/]"
    return f"[bold red]🔴 {score}/100[/]"


def _trend_icon(trend: str) -> str:
    """Trend indicator with icon."""
    icons = {"growing": "📈 growing", "stable": "📊 stable", "declining": "📉 declining"}
    colors = {"growing": "green", "stable": "cyan", "declining": "red"}
    return f"[{colors.get(trend, 'white')}]{icons.get(trend, trend)}[/]"


def _sparkline(velocity: dict[str, int], width: int = 20) -> str:
    """Render last N days as a Unicode sparkline."""
    if not velocity:
        return "[dim]no data[/]"
    sparks = "▁▂▃▄▅▆▇█"
    sorted_days = sorted(velocity.keys())[-width:]
    values = [velocity[d] for d in sorted_days]
    v_max = max(values) if values else 1
    if v_max == 0:
        return "▁" * len(values)
    return "".join(sparks[min(int(v / v_max * 7), 7)] for v in values)


def _render_shannon_table(result: dict[str, Any]) -> None:
    from rich.table import Table

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Dimension", style="bold white")
    table.add_column("H (bits)", justify="right")
    table.add_column("H_max", justify="right")
    table.add_column("Normalized", justify="right")
    table.add_column("Redundancy", justify="right")
    table.add_column("Bar", min_width=22)

    for dim_name, dim_key in [
        ("Type", "type_entropy"),
        ("Confidence", "confidence_entropy"),
        ("Project", "project_entropy"),
        ("Source", "source_entropy"),
        ("Age", "age_entropy"),
        ("Content", "content_entropy"),
    ]:
        block = result[dim_key]
        norm = block["normalized"]
        r = block["redundancy"]
        color = "green" if 0.3 <= norm <= 0.9 else "red"
        if r < 0.5:
            r_color = "green"
        elif r < 0.7:
            r_color = "yellow"
        else:
            r_color = "red"
        table.add_row(
            dim_name,
            str(block["H"]),
            str(block["H_max"]),
            f"[{color}]{norm:.2%}[/]",
            f"[{r_color}]{r:.2%}[/]",
            f"[{color}]{_bar(norm)}[/]",
        )

    console.print(table)


def _render_shannon_verbose(result: dict[str, Any]) -> None:
    from rich.table import Table

    for dim_name, dim_key in [
        ("Type", "type_entropy"),
        ("Confidence", "confidence_entropy"),
        ("Source", "source_entropy"),
        ("Content", "content_entropy"),
    ]:
        dist = result[dim_key]["distribution"]
        if not dist:
            continue
        detail = Table(
            title=f"{dim_name} Breakdown",
            show_header=True,
            header_style="dim",
        )
        detail.add_column("Category", style="white")
        detail.add_column("Count", justify="right")
        detail.add_column("Share", justify="right")
        total_dim = sum(dist.values())
        for cat, cnt in sorted(dist.items(), key=lambda x: -x[1]):
            share = cnt / total_dim if total_dim else 0
            detail.add_row(cat, str(cnt), f"{share:.1%}")
        console.print(detail)


def _render_shannon_diagnosis(result: dict[str, Any]) -> None:
    from rich.panel import Panel

    mi = result["mutual_info_type_project"]
    console.print(f"\n[bold white]I(type; project)[/] = [noir.cyber]{mi:.4f}[/] bits")

    diag = result["diagnosis"]
    diag_colors = {
        "balanced": "green",
        "concentrated": "yellow",
        "fragmented": "red",
        "stale": "magenta",
        "redundant": "yellow",
        "declining": "red",
    }
    color = diag_colors.get(diag, "white")
    console.print(f"[bold white]Diagnosis:[/] [{color}]{diag.upper()}[/]\n")

    for rec in result["recommendations"]:
        console.print(
            Panel(
                f"[white]{rec}[/]",
                border_style="dim",
                padding=(0, 1),
            )
        )


@entropy.command("immortality")
@click.option("--project", "-p", default=None, help="Filter by project.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
@click.option("--verbose", "-v", is_flag=True, help="Dimension detail.")
def entropy_immortality(
    project: str | None,
    as_json: bool,
    verbose: bool,
) -> None:
    """Immortality Index (ι) — cognitive crystallization metric."""
    from cortex.extensions.shannon.immortality import ImmortalityIndex

    engine = get_engine()
    try:
        result = _run_async(ImmortalityIndex.compute(engine, project))

        if as_json:
            # Strip Rich markup from badge for clean JSON
            clean = {k: v for k, v in result.items() if k != "badge"}
            console.print_json(json_mod.dumps(clean, indent=2))
            return

        # ── Header ───────────────────────────────────────────
        title = "⚡ IMMORTALITY INDEX (ι)"
        if project:
            title += f"  ·  {project}"
        console.print(
            f"\n[noir.cyber]{title}[/]  "
            f"[dim]({result['total_facts']} facts · "
            f"{result['active_days']} active days · "
            f"{result['total_span_days']}d span)[/]\n"
        )
        console.print(f"  {result['badge']}\n")

        # ── Dimension table ──────────────────────────────────
        from rich.table import Table

        dim_table = Table(show_header=True, header_style="bold cyan")
        dim_table.add_column("Dimension", style="bold white")
        dim_table.add_column("Symbol", justify="center")
        dim_table.add_column("Score", justify="right")
        dim_table.add_column("Weight", justify="right")
        dim_table.add_column("Bar", min_width=22)

        symbols = {
            "diversity": "δ",
            "continuity": "γ",
            "density": "ρ",
            "quality": "κ",
            "coverage": "σ",
        }
        for name, dim in result["dimensions"].items():
            score = dim["pct"]
            color = "green" if score >= 75 else "yellow" if score >= 45 else "red"
            dim_table.add_row(
                name.capitalize(),
                symbols.get(name, "?"),
                f"[{color}]{score:.1f}%[/]",
                f"{dim['weight']:.0%}",
                f"[{color}]{dim['bar']}[/]",
            )
        console.print(dim_table)

        # ── Weakest dimension ────────────────────────────────
        from rich.panel import Panel

        weak = result["weakest"]
        console.print(
            Panel(
                f"[bold white]{weak['dimension'].upper()}[/] "
                f"({weak['score']:.0%})\n\n"
                f"[white]{weak['recommendation']}[/]",
                title="[bold red]⚠ Weakest Dimension[/]",
                border_style="red",
                padding=(1, 2),
            )
        )

        if verbose:
            console.print(f"\n[dim]Max temporal gap: {result['max_gap_days']}d[/]")
            diag = result["diagnosis"].replace("_", " ").upper()
            console.print(f"[dim]Diagnosis: {diag}[/]")

    except (OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, context="immortality index")
    finally:
        close_engine_sync(engine)


@entropy.command("shannon")
@click.option("--project", "-p", default=None, help="Filter by project.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show per-category breakdown.",
)
def entropy_shannon(project: str | None, as_json: bool, verbose: bool) -> None:
    """Shannon entropy analysis of CORTEX memory."""
    from cortex.extensions.shannon.report import EntropyReport

    engine = get_engine()
    try:
        result = _run_async(EntropyReport.analyze(engine, project))

        if as_json:
            console.print_json(json_mod.dumps(result, indent=2))
            return

        title = "🧠 SHANNON ENTROPY REPORT"
        if project:
            title += f"  ·  {project}"
        health = result["health_score"]
        console.print(f"\n[noir.cyber]{title}[/]  [dim]({result['total_facts']} active facts)[/]\n")

        console.print(
            f"  Health: {_health_badge(health)}"
            f"    Trend: {_trend_icon(result['temporal_trend'])}"
            f"    Velocity: {_sparkline(result['velocity_per_day'])}\n"
        )

        _render_shannon_table(result)

        if verbose:
            _render_shannon_verbose(result)

        _render_shannon_diagnosis(result)

    except (OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, context="shannon analysis")
    finally:
        close_engine_sync(engine)
