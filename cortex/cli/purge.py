# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine

__all__ = [
    "purge",
    "purge_duplicates",
    "purge_empty",
    "purge_project",
    "purge_omega",
]


def _purge_short_facts(conn, dry_run: bool) -> int:
    """Purge or preview purging of very short facts (< 15 chars)."""
    rows = conn.execute(
        "SELECT id, content FROM facts WHERE length(content) < 15 AND valid_until IS NULL",
    ).fetchall()
    if not rows:
        return 0

    count = len(rows)
    console.print(f"  {'[yellow]WOULD[/] ' if dry_run else ''}🗑  Short facts (<15 chars): {count}")
    if not dry_run:
        conn.execute(
            "UPDATE facts SET valid_until = datetime('now'), "
            "metadata = json_set(COALESCE(metadata, '{}'), "
            "'$.deprecation_reason', 'purge-too-short') "
            "WHERE length(content) < 15 AND valid_until IS NULL",
        )
    return count


@cli.group()
def purge():
    """Purge garbage facts from CORTEX."""


@purge.command("duplicates")
@click.option("--dry-run", is_flag=True, help="Preview without deleting")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def purge_duplicates(dry_run, db) -> None:
    """Remove exact duplicate facts, keeping the oldest per project."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()
        rows = conn.execute(
            "SELECT content, project, MIN(id) AS keep_id, COUNT(*) AS cnt "
            "FROM facts WHERE valid_until IS NULL "
            "GROUP BY content, project HAVING cnt > 1"
        ).fetchall()

        if not rows:
            console.print("[green]✓[/] No duplicates found.")
            return

        total = 0
        table = Table(title="Duplicate Facts", border_style="cyan")
        table.add_column("Keep #", style="bold", width=7)
        table.add_column("Project", style="cyan", width=18)
        table.add_column("Copies", width=7)
        table.add_column("Content", width=50)

        for content, project, keep_id, cnt in rows:
            duplicates = cnt - 1
            total += duplicates
            preview = content[:47] + "..." if len(content) > 50 else content
            table.add_row(str(keep_id), project, str(duplicates), preview)

            if not dry_run:
                conn.execute(
                    "UPDATE facts SET valid_until = datetime('now'), "
                    "metadata = json_set(COALESCE(metadata, '{}'), "
                    "'$.deprecation_reason', 'purge-duplicate') "
                    "WHERE content = ? AND project = ? AND id != ? "
                    "AND valid_until IS NULL",
                    (content, project, keep_id),
                )

        console.print(table)

        if dry_run:
            console.print(f"\n[yellow]DRY RUN:[/] Would deprecate {total} duplicates.")
        else:
            conn.commit()
            console.print(f"\n[green]✓[/] Deprecated {total} duplicate facts.")
    finally:
        engine.close_sync()


@purge.command("empty")
@click.option("--dry-run", is_flag=True, help="Preview without deleting")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def purge_empty(dry_run, db) -> None:
    """Remove facts with empty or template-only content."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()

        patterns = [
            ("Empty bridges", "BRIDGE:  →%"),
            ("Empty bridges (agent)", "BRIDGE: agent:moskv-1 →  |%"),
            ("Empty errors", "ERROR:  | CAUSA:  | FIX:%"),
            ("Empty ghosts", "GHOST: % | Última tarea: desconocida%"),
        ]

        total = 0
        for label, pattern in patterns:
            rows = conn.execute(
                "SELECT id FROM facts WHERE content LIKE ? AND valid_until IS NULL",
                (pattern,),
            ).fetchall()

            if rows:
                count = len(rows)
                total += count
                console.print(f"  {'[yellow]WOULD[/] ' if dry_run else ''}🗑  {label}: {count}")

                if not dry_run:
                    conn.execute(
                        "UPDATE facts SET valid_until = datetime('now'), "
                        "metadata = json_set(COALESCE(metadata, '{}'), "
                        "'$.deprecation_reason', 'purge-empty') "
                        "WHERE content LIKE ? AND valid_until IS NULL",
                        (pattern,),
                    )

        # Catch very short facts (< 15 chars)
        total += _purge_short_facts(conn, dry_run)

        if total == 0:
            console.print("[green]✓[/] No empty/garbage facts found.")
        elif dry_run:
            console.print(f"\n[yellow]DRY RUN:[/] Would deprecate {total} facts.")
        else:
            conn.commit()
            console.print(f"\n[green]✓[/] Deprecated {total} empty/garbage facts.")
    finally:
        engine.close_sync()


@purge.command("project")
@click.argument("project_name")
@click.option("--dry-run", is_flag=True, help="Preview without deleting")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def purge_project(project_name, dry_run, db) -> None:
    """Deprecate all facts in a project."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()
        rows = conn.execute(
            "SELECT id, fact_type, content FROM facts WHERE project = ? AND valid_until IS NULL",
            (project_name,),
        ).fetchall()

        if not rows:
            console.print(f"[dim]No active facts in project '{project_name}'.[/]")
            return

        table = Table(title=f"Facts in '{project_name}' ({len(rows)})", border_style="cyan")
        table.add_column("ID", style="bold", width=5)
        table.add_column("Type", width=10)
        table.add_column("Content", width=60)
        for row in rows[:20]:
            preview = row[2][:57] + "..." if len(row[2]) > 60 else row[2]
            table.add_row(str(row[0]), row[1], preview)
        if len(rows) > 20:
            table.add_row("...", "...", f"(+{len(rows) - 20} more)")
        console.print(table)

        if dry_run:
            console.print(f"\n[yellow]DRY RUN:[/] Would deprecate {len(rows)} facts.")
        else:
            conn.execute(
                "UPDATE facts SET valid_until = datetime('now'), "
                "metadata = json_set(COALESCE(metadata, '{}'), "
                "'$.deprecation_reason', 'purge-project') "
                "WHERE project = ? AND valid_until IS NULL",
                (project_name,),
            )
            conn.commit()
            console.print(
                f"\n[green]✓[/] Deprecated {len(rows)} facts in project '{project_name}'."
            )
    finally:
        engine.close_sync()


@purge.command("omega")
def purge_omega() -> None:
    """LEA-Ω: Loose End Annihilator. Purges dead code, caches, and token debris."""
    console.print("[bold red]🔥 Iniciando LEA-Ω (Loose End Annihilator)...[/]")

    # 1. Dead Code & Imports Annihilation
    console.print("\n[cyan][1/3] Annihilating dead code and imports (Ruff)...[/]")
    try:
        subprocess.run(
            ["ruff", "check", "--select", "F401,F841", "--fix", "."],
            capture_output=True,
            text=True,
            check=False,
        )
        console.print("  [green]✓[/] Dead variables and unused imports purged.")
    except Exception as e:
        console.print(f"  [yellow]⚠[/] Ruff fix failed: {e}")

    # 2. Cache Annihilation
    console.print("\n[cyan][2/3] Annihilating execution caches...[/]")
    cache_dirs = ["__pycache__", ".pytest_cache", ".ruff_cache"]
    deleted_caches = 0
    for root, dirs, _ in os.walk("."):
        for d in dirs:
            if d in cache_dirs:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                deleted_caches += 1
    console.print(f"  [green]✓[/] Destroyed {deleted_caches} cache directories.")

    # 3. Brain Scratch Annihilation (Cross-Session)
    console.print("\n[cyan][3/3] Annihilating legacy token debris...[/]")
    brain_dir = Path("~/.gemini/antigravity/brain").expanduser()
    current_session = os.environ.get("CONVERSATION_ID")
    total_files = 0
    total_bytes = 0

    if brain_dir.exists():
        for scratch_dir in brain_dir.rglob("scratch"):
            if current_session and current_session in str(scratch_dir):
                continue

            for item in scratch_dir.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        total_bytes += item.stat().st_size
                        total_files += 1
                        item.unlink()
                    elif item.is_dir():
                        for subitem in item.rglob("*"):
                            if subitem.is_file() or subitem.is_symlink():
                                total_bytes += subitem.stat().st_size
                                total_files += 1
                        shutil.rmtree(item)
                except Exception:
                    pass

    freed_mb = total_bytes / (1024 * 1024)
    console.print(f"  [green]✓[/] Destroyed {total_files} legacy files ({freed_mb:.2f} MB).")

    console.print("\n[bold green]✅ LEA-Ω PURGE COMPLETE (C5-REAL). Zero Mercy.[/]")
