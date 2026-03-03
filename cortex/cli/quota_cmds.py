"""CLI commands: quota (PULMONES — Sovereign Quota Manager)."""

from __future__ import annotations

import dataclasses
import json

import click
from rich.table import Table

from cortex.cli.common import console
from cortex.llm.quota import SovereignQuotaManager


@click.group()
def quota_cli() -> None:
    """Métricas y estrangulamiento de la cuota Antigravity (PULMONES)."""


@quota_cli.command()
@click.option("--json-output", is_flag=True, help="Output status as JSON")
def status(json_output) -> None:
    """Visualiza el estado del Sovereign Quota Manager con métricas."""
    mgr = SovereignQuotaManager()
    stats = mgr.status()

    if json_output:
        click.echo(json.dumps(dataclasses.asdict(stats), indent=2))
        return

    table = Table(
        title="[bold #CCFF00]🫁 SOVEREIGN QUOTA MANAGER (PULMONES)[/]",
        border_style="#6600FF",
    )
    table.add_column("Métrica", style="bold #D4AF37")
    table.add_column("Valor", style="cyan", justify="right")

    table.add_row("Protocolo Operativo", "[bold #06d6a0]Activo 130/100[/]")
    table.add_section()

    # ── Bucket ────────────────────────────────────────────────────────────
    table.add_row("Capacidad Máxima", f"{stats.capacity} tokens (RPM)")
    table.add_row(
        "Tokens Actuales",
        f"[bold white]{stats.current_tokens}[/] ({stats.fill_pct}%)",
    )
    table.add_row("Tasa de Recarga", f"{stats.refill_rate_per_s} tok/s")

    time_to_full = stats.time_to_full_s
    color = "#06d6a0" if time_to_full == 0 else "yellow"
    table.add_row("Tiempo para 100%", f"[{color}]{time_to_full}s[/]")

    # ── Métricas de observabilidad ────────────────────────────────────────
    table.add_section()
    ratio_color = "#06d6a0" if stats.throttle_ratio_pct < 10 else "red"
    table.add_row("Adquiridos (OK)", f"[bold]{stats.acquired}[/]")
    table.add_row("Estrangulados", f"[yellow]{stats.throttled}[/]")
    table.add_row("Timeouts", f"[red]{stats.timeouts}[/]")
    table.add_row(
        "Throttle Ratio",
        f"[{ratio_color}]{stats.throttle_ratio_pct}%[/]",
    )

    console.print(table)

    if stats.current_tokens < 1.0:
        console.print(
            "\n[yellow]⚠️  ALERTA PULMONES: Sistema estrangulado."
            " La próxima llamada API entrará en sleep asíncrono.[/yellow]"
        )


@quota_cli.command()
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirmar el reset de emergencia sin prompt interactivo.",
)
def reset(confirm: bool) -> None:
    """Reset de emergencia: llena el bucket al máximo y borra métricas.

    \b
    ⚠️  Uso: solo en situaciones de emergencia (bloqueo total del sistema).
    Resetea contadores acquired/throttled/timeouts a 0.
    """
    if not confirm:
        click.confirm(
            "⚠️  ¿Confirmas el reset de emergencia del Sovereign Quota Manager?",
            abort=True,
        )

    mgr = SovereignQuotaManager()
    mgr.reset()
    console.print(
        f"[bold #CCFF00]✅ PULMONES RESET:[/] Bucket restaurado a"
        f" [bold]{int(mgr.capacity)}[/] tokens. Métricas borradas."
    )
