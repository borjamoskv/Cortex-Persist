"""CLI commands: mejoralo scan, record, history, ship."""

from __future__ import annotations

import click
from rich.table import Table

from cortex.cli import DEFAULT_DB, cli, console, get_engine

__all__ = [
    "mejoralo",
    "mejoralo_history",
    "mejoralo_record",
    "mejoralo_scan",
    "mejoralo_ship",
    "mejoralo_daemon",
]


@cli.group()
def mejoralo():
    """MEJORAlo v8.0 — Protocolo de auditoría y mejora de código. Modo Relentless."""
    pass


@mejoralo.command("scan")
@click.argument("project")
@click.argument("path", type=click.Path(exists=True))
@click.option("--deep", is_flag=True, help="Activa dimensión Psi + análisis profundo")
@click.option("--brutal", is_flag=True, help="Intensidad máxima (deep + penalizaciones duplicadas)")
@click.option(
    "--auto-heal", is_flag=True, help="Intenta curar el código autónomamente si score < 70"
)
@click.option("--relentless", is_flag=True, help="♾️ INMEJORABLE: no para hasta score ≥ 95")
@click.option(
    "--target-score", type=int, default=None, help="Score objetivo personalizado (default: 70 o 95)"
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_scan(project, path, deep, brutal, auto_heal, relentless, target_score, db):
    """X-Ray 13D — Escaneo multidimensional del proyecto."""
    from cortex.mejoralo import MejoraloEngine
    from cortex.mejoralo.constants import INMEJORABLE_SCORE

    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        with console.status("[bold blue]Ejecutando X-Ray 13D...[/]"):
            result = m.scan(project, path, deep=deep, brutal=brutal)

        _display_scan_result(result)

        if relentless:
            effective_target = target_score if target_score is not None else INMEJORABLE_SCORE
            console.print(
                f"\n[bold magenta]♾️ MODO RELENTLESS ACTIVADO — "
                f"Meta: {effective_target}/100. No hay vuelta atrás.[/]"
            )
            success = m.relentless_heal(project, path, result, target_score=effective_target)
            if success:
                console.print(
                    "[bold green]✅ Código purificado. Nivel INMEJORABLE alcanzado. (+Soberanía)[/]"
                )
            else:
                console.print("[bold red]❌ Relentless abortado. La deuda técnica persiste.[/]")
        elif auto_heal and result.score < (target_score or 70):
            effective_target = target_score or 70
            console.print(
                f"\n[yellow]⚠️ Auto-Heal Activado: Score por debajo de {effective_target}.[/]"
            )
            success = m.heal(project, path, effective_target, result)
            if success:
                console.print(
                    "[bold green]✅ Código purificado y comiteado automáticamente. (+Soberanía)[/]"
                )
            else:
                console.print("[bold red]❌ Auto-Heal abortado. La deuda técnica persiste.[/]")
    finally:
        engine.close_sync()


def _display_scan_result(result):
    """Format and print scan results to the console."""
    if result.score >= 80:
        score_style = "bold green"
    elif result.score >= 50:
        score_style = "bold yellow"
    else:
        score_style = "bold red"

    table = Table(title=f"🔬 X-Ray 13D — {result.project}")
    table.add_column("Dimensión", style="bold", width=15)
    table.add_column("Score", width=8)
    table.add_column("Peso", width=10)
    table.add_column("Hallazgos", width=50)

    for d in result.dimensions:
        if d.score >= 80:
            d_color = "green"
        elif d.score >= 50:
            d_color = "yellow"
        else:
            d_color = "red"
        findings_str = "; ".join(d.findings[:3]) if d.findings else "—"
        table.add_row(d.name, f"[{d_color}]{d.score}[/]", d.weight, findings_str[:50])

    console.print(table)

    mode_str = " | [bold red]BRUTAL[/]" if result.brutal else ""
    console.print(
        f"\n  Stack: [cyan]{result.stack}[/] | "
        f"Archivos: {result.total_files} | "
        f"LOC: {result.total_loc:,} | "
        f"Score: [{score_style}]{result.score}/100[/]{mode_str}"
    )

    if result.dead_code:
        console.print("  [bold red]☠️  CÓDIGO MUERTO (score < 50)[/]")


@mejoralo.command("record")
@click.argument("project")
@click.option("--before", "score_before", type=int, required=True, help="Score antes")
@click.option("--after", "score_after", type=int, required=True, help="Score después")
@click.option("--action", "-a", "actions", multiple=True, help="Acciones realizadas (repetible)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_record(project, score_before, score_after, actions, db):
    """Ouroboros — Registrar sesión MEJORAlo en el ledger."""
    from cortex.mejoralo import MejoraloEngine

    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        fact_id = m.record_session(
            project=project,
            score_before=score_before,
            score_after=score_after,
            actions=list(actions),
        )
        delta = score_after - score_before
        if delta > 0:
            color = "green"
        elif delta < 0:
            color = "red"
        else:
            color = "yellow"

        # Update mejora_loop_state.json if it exists
        import json
        from datetime import datetime
        from pathlib import Path

        state_file = Path.home() / ".cortex" / "mejora_loop_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                if "improvement_history" not in state:
                    state["improvement_history"] = []
                state["improvement_history"].append(
                    {
                        "project": project,
                        "timestamp": datetime.now().isoformat(),
                        "score_before": score_before,
                        "score_after": score_after,
                        "delta": delta,
                    }
                )
                state["improvement_history"] = state["improvement_history"][-100:]
                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2, default=str)
            except (OSError, ValueError):
                pass

        console.print(
            f"[green]✓[/] Sesión registrada [bold]#{fact_id}[/] — "
            f"{score_before} → {score_after} ([{color}]Δ{delta:+d}[/])"
        )
    finally:
        engine.close_sync()


@mejoralo.command("history")
@click.argument("project")
@click.option("--limit", "-n", default=10, help="Máximo de resultados")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_history(project, limit, db):
    """Historial de sesiones MEJORAlo."""
    from cortex.mejoralo import MejoraloEngine

    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        sessions = m.history(project, limit=limit)
        if not sessions:
            console.print(f"[dim]Sin sesiones MEJORAlo para '{project}'.[/]")
            return
        table = Table(title=f"📊 MEJORAlo History — {project}")
        table.add_column("ID", style="bold", width=6)
        table.add_column("Fecha", width=20)
        table.add_column("Score", width=12)
        table.add_column("Δ", width=6)
        table.add_column("Acciones", width=40)
        for s in sessions:
            delta = s.get("delta", 0)
            if delta and delta > 0:
                d_color = "green"
            elif delta and delta < 0:
                d_color = "red"
            else:
                d_color = "dim"

            s_before = s.get("score_before", "?")
            s_after = s.get("score_after", "?")
            score_str = f"{s_before} → {s_after}"
            actions_str = ", ".join(s.get("actions", [])[:2]) or "—"
            table.add_row(
                str(s["id"]),
                s["created_at"][:19].replace("T", " "),
                score_str,
                f"[{d_color}]{delta:+d}[/]" if delta is not None else "—",
                actions_str[:40],
            )
        console.print(table)
    finally:
        engine.close_sync()


@mejoralo.command("ship")
@click.argument("project")
@click.argument("path", type=click.Path(exists=True))
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_ship(project, path, db):
    """Ship Gate — Los 7 Sellos de producción."""
    from cortex.mejoralo import MejoraloEngine

    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        with console.status("[bold blue]Validando los 7 Sellos...[/]"):
            result = m.ship_gate(project, path)
        for seal in result.seals:
            icon = "[green]✓[/]" if seal.passed else "[red]✗[/]"
            console.print(f"  {icon} {seal.name}: {seal.detail}")
        console.print()
        if result.ready:
            console.print(
                f"  [bold green]🚀 READY — {result.passed}/{result.total} sellos aprobados[/]"
            )
        else:
            console.print(
                f"  [bold red]⛔ NOT READY — {result.passed}/{result.total} sellos aprobados[/]"
            )
    finally:
        engine.close_sync()


@mejoralo.command("daemon")
def mejoralo_daemon():
    """♾️  Ouroboros — Inicia el bucle infinito de mejora soberana."""
    from cortex.mejoralo.daemon import main
    main()
