"""
CORTEX CLI — NotebookLM Integration Commands.

Provides native CLI commands for NotebookLM synchronization:
  cortex notebooklm digest    → Generate Master Digest
  cortex notebooklm fragment  → Domain-based fragmentation
  cortex notebooklm sync      → Export to Google Drive folder
  cortex notebooklm status    → Show sync status
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.config import DEFAULT_DB_PATH

console = Console()

# ── Constants ──────────────────────────────────────────────────────────
NOTEBOOKLM_DIR = Path("notebooklm_sources")
DOMAINS_DIR = Path("notebooklm_domains")
DIGEST_FILE = Path("cortex_notebooklm_digest.md")

# Default Google Drive sync path (macOS)
GDRIVE_DEFAULT = (
    Path.home() / "Library" / "CloudStorage"
    / "GoogleDrive-borjafernandezangulo@gmail.com"
    / "Mi unidad" / "CORTEX-NotebookLM"
)
GDRIVE_ALT = Path.home() / "Google Drive" / "CORTEX-NotebookLM"

# Domain taxonomy
DOMAIN_MAP: dict[str, list[str]] = {
    "cortex-core": [
        "cortex", "CORTEX", "CORTEX-Core", "CORTEX-V8", "CORTEX V8",
        "CORTEX V7 Evolution", "CORTEX V8 Transition", "CORTEX_V7",
        "CORTEX-LLM", "CORTEX-Formatter", "CORTEX-Evolution",
        "CORTEX-Daemon", "CORTEX_CLOUD", "cortex-v7", "cortex-test",
        "cortex-persist", "Cortex-Persist", "cortexpersist", "cli",
        "CORE", "CODEX", "__system__",
    ],
    "cortex-infra": [
        "SYSTEM", "system", "daemons", "security", "scripts",
        "DNS / CNS Config", "macOS", "MACOS_TAHOE", "sidecar",
        "testing", "test-project", "TEST", "default",
    ],
    "cortex-agents": [
        "AGENT_SCIENCE", "AGENTICA", "moskv-swarm", "swarm-demo",
        "MOSKV-1", "MOSKV", "moskv-1", "moskv", "__bridges__",
        "nexus", "singularity-nexus", "centauro", "agent:gemini",
        "pydantic-ai", "kimi-swarm-1", "KIMI",
    ],
    "cortex-products": [
        "naroa", "naroa-2026", "naroa-web", "NAROA_2026",
        "live-notch", "live-notch-swift", "livenotch", "notch-live",
        "cortex-notch", "SonicNotch", "moltbook", "MOLTBOOK",
        "Moltbook", "Moltbook Ledger", "Moltbook Monetization",
        "sonic-supreme", "sonic_sovereign", "mastering-1",
        "lyria-studio", "veo-lyria-studio", "filete-cumbia",
        "el-pueblo-online", "gordacorp", "borjamoskv", "borjamoskv.com",
        "borja.moskv.eth", "manteca-web", "comienzos-clone",
        "xokas-elevator", "garmin-dashboard", "millennium",
        "openclaw", "conspiracy-calculator", "RATIOHEAD",
        "noir-ui-kit", "impact-web", "FrontierApp",
    ],
    "cortex-operations": [
        "ghost-control", "ghost_control", "GHOST-1", "GHOST-CONTROL",
        "autorouter", "autorouter-1", "SAP", "sap", "SAP Audit",
        "SAP_SYNC", "sap-audit-ui", "mailtv-1", "MAILTV-1",
        "MAILING", "ecosistema", "global", "general",
        "reporting", "tips", "i18n", "IDC", "idc-agent",
        "JMIR", "JMIR-FREE-PUB-COMPLETED", "JMIR-FREE-TIERS",
        "EU_SCRAPER", "REDDIT_OVERLORD", "omni-translate",
    ],
    "cortex-strategy": [
        "COMMERCE-Ω", "Pricing", "ROI_LABOR", "moneytv", "moneytv-1",
        "cortex-landing", "landing", "landing-apotheosis",
        "CortexSovereignWeb", "cortex-sovereign-web",
        "moskvbot", "moskvbot-test",
    ],
    "cortex-research": [
        "EVOLUTION", "evolution", "Ouroboros", "ouroboros",
        "TEMPORAL", "TEMPORAL-RENAMING", "TEMPORAL-UNIFICATION",
        "SINGULARITY-OMEGA", "PORTAL-OMEGA", "VOID-SINGULARITY",
        "Synaptic/Causal", "APOTHEOSIS", "AUTODIDACT", "AUTO_MUTATE",
        "CHRONOS-1", "Sovereignty", "aether-omega", "keter",
        "keter-omega", "antigravity", "Antigravity",
        "Antigravity/CORTEX", "Antigravity/Ghost/MCP",
        "blue", "MANT_SYS", "OLA3", "mejoralo",
        "Muro de Aislamiento", "eqmac-re",
    ],
}

_PROJECT_DOMAIN: dict[str, str] = {}
for _domain, _projs in DOMAIN_MAP.items():
    for _p in _projs:
        _PROJECT_DOMAIN[_p] = _domain


def _get_db_path() -> str:
    return str(DEFAULT_DB_PATH)


def _get_facts_df():
    """Load active facts from CORTEX DB."""
    import pandas as pd
    conn = sqlite3.connect(_get_db_path())
    df = pd.read_sql_query(
        "SELECT project, fact_type, content, confidence, tags "
        "FROM facts WHERE valid_until IS NULL",
        conn,
    )
    conn.close()
    return df


def _detect_gdrive() -> Path | None:
    """Detect Google Drive sync folder."""
    for candidate in [GDRIVE_DEFAULT, GDRIVE_ALT]:
        if candidate.parent.exists():
            return candidate
    return None


def _format_fact_line(row) -> str:
    """Format a single fact as markdown line."""
    conf = row.get("confidence", "stated")
    tags_raw = row.get("tags", "[]")
    line = f"- {row['content']}"
    if conf and conf != "stated":
        line += f" *(conf: {conf})*"
    if tags_raw and tags_raw != "[]":
        try:
            tag_list = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
            if tag_list:
                line += f" `{', '.join(tag_list)}`"
        except (ValueError, TypeError):
            pass
    return line


# ── CLI Group ──────────────────────────────────────────────────────────

@click.group("notebooklm")
def notebooklm_cmds():
    """📓 NotebookLM synchronization commands."""
    pass


@notebooklm_cmds.command("digest")
@click.option("--output", "-o", type=click.Path(), default=str(DIGEST_FILE),
              help="Output file path")
def digest_cmd(output: str):
    """Generate Master Digest for NotebookLM (all-in-one)."""
    df = _get_facts_df()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    projects = sorted(df["project"].unique())

    lines = [
        "# 🧠 CORTEX MASTER KNOWLEDGE DIGEST\n\n",
        f"> Snapshot: {ts} | Facts: {len(df)} | Projects: {len(projects)}\n\n",
        "---\n\n",
    ]

    for proj in projects:
        proj_df = df[df["project"] == proj]
        lines.append(f"## {proj}\n*{len(proj_df)} hechos*\n\n")
        for ftype in sorted(proj_df["fact_type"].unique()):
            lines.append(f"### {ftype.capitalize()}\n")
            for _, row in proj_df[proj_df["fact_type"] == ftype].iterrows():
                lines.append(_format_fact_line(row) + "\n")
            lines.append("\n")
        lines.append("---\n\n")

    content = "".join(lines)
    Path(output).write_text(content, encoding="utf-8")

    word_count = len(content.split())
    limit_msg = (
        '✅ Dentro del límite (500K words)'
        if word_count < 500_000
        else '⚠️ EXCEDE 500K words!'
    )
    console.print(Panel(
        f"[green]✅ Master Digest generado[/green]\n"
        f"  Archivo: {output}\n"
        f"  Facts: {len(df):,}\n"
        f"  Proyectos: {len(projects)}\n"
        f"  Caracteres: {len(content):,}\n"
        f"  Palabras: {word_count:,}\n"
        f"  {limit_msg}",
        title="📓 NotebookLM Digest",
        border_style="green",
    ))


@notebooklm_cmds.command("fragment")
@click.option("--output-dir", "-o", type=click.Path(), default=str(DOMAINS_DIR),
              help="Output directory for domain fragments")
def fragment_cmd(output_dir: str):
    """Fragment knowledge into semantic domains."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    df = _get_facts_df()
    df["domain"] = df["project"].apply(lambda p: _PROJECT_DOMAIN.get(p, "cortex-misc"))
    ts = datetime.now().strftime("%Y-%m-%d")

    table = Table(title="📓 Domain Fragmentation")
    table.add_column("Domain", style="cyan")
    table.add_column("Facts", justify="right")
    table.add_column("%", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Status")

    total_facts = len(df)
    for domain in sorted(df["domain"].unique()):
        domain_df = df[df["domain"] == domain]
        projects_in = sorted(domain_df["project"].unique())
        filename = out / f"{domain}-{ts}.md"

        lines = [
            f"# 🧠 CORTEX — {domain.upper()}\n\n",
            f"> Snapshot: {ts} | Facts: {len(domain_df)} | Projects: {len(projects_in)}\n\n",
            "---\n\n",
        ]
        for proj in projects_in:
            proj_df = domain_df[domain_df["project"] == proj]
            lines.append(f"## {proj}\n*{len(proj_df)} hechos*\n\n")
            for ftype in sorted(proj_df["fact_type"].unique()):
                lines.append(f"### {ftype.capitalize()}\n")
                for _, row in proj_df[proj_df["fact_type"] == ftype].iterrows():
                    lines.append(_format_fact_line(row) + "\n")
                lines.append("\n")
            lines.append("---\n\n")

        content = "".join(lines)
        filename.write_text(content, encoding="utf-8")
        word_count = len(content.split())
        pct = (len(domain_df) / total_facts * 100) if total_facts else 0
        status = "[green]✅[/green]" if word_count < 500_000 else "[red]⚠️ OVER[/red]"
        table.add_row(domain, str(len(domain_df)), f"{pct:.1f}%", f"{word_count:,}", status)

    console.print(table)
    console.print(f"\n📁 Output: {out}/")


@notebooklm_cmds.command("sync")
@click.option("--drive-path", type=click.Path(), default=None,
              help="Google Drive folder path (auto-detected if not set)")
@click.option("--mode", type=click.Choice(["digest", "domains", "both"]),
              default="both", help="What to sync")
def sync_cmd(drive_path: str | None, mode: str):
    """Sync exports to Google Drive for NotebookLM auto-pickup."""
    # Detect or use provided path
    if drive_path:
        target = Path(drive_path)
    else:
        target = _detect_gdrive()
        if not target:
            console.print("[red]❌ Google Drive no detectado.[/red]")
            console.print("Especifica --drive-path manualmente o instala Google Drive for Desktop.")
            return

    target.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    synced_files = []

    if mode in ("digest", "both"):
        digest_path = Path(DIGEST_FILE)
        if not digest_path.exists():
            console.print("[yellow]Generando digest...")
            ctx = click.Context(digest_cmd, info_name="digest")
            ctx.invoke(digest_cmd, output=str(DIGEST_FILE))

        dest = target / f"cortex-master-{ts}.md"
        shutil.copy2(DIGEST_FILE, dest)
        synced_files.append(str(dest))

    if mode in ("domains", "both"):
        domains_path = Path(DOMAINS_DIR)
        if not domains_path.exists() or not any(domains_path.glob("*.md")):
            console.print("[yellow]Generando fragmentos de dominio...[/yellow]")
            ctx = click.Context(fragment_cmd, info_name="fragment")
            ctx.invoke(fragment_cmd, output_dir=str(DOMAINS_DIR))

        for f in domains_path.glob("*.md"):
            dest = target / f.name
            shutil.copy2(f, dest)
            synced_files.append(str(dest))

    # Clean old files (older than 7 days)
    import os
    import time
    cutoff = time.time() - (7 * 86400)
    cleaned = 0
    for f in target.glob("*.md"):
        synced_names = [Path(s).name for s in synced_files]
        if os.path.getmtime(f) < cutoff and f.name not in synced_names:
            f.unlink()
            cleaned += 1

    console.print(Panel(
        f"[green]✅ Sincronizados {len(synced_files)} archivos[/green]\n"
        f"  Destino: {target}\n"
        f"  {'Limpiados ' + str(cleaned) + ' archivos antiguos' if cleaned else ''}\n\n"
        f"  📋 NotebookLM debería detectarlos automáticamente\n"
        f"     si Drive está conectado como fuente.",
        title="🔄 Google Drive Sync",
        border_style="green",
    ))


@notebooklm_cmds.command("status")
def status_cmd():
    """Show NotebookLM sync status and file inventory."""
    table = Table(title="📓 NotebookLM Integration Status")
    table.add_column("Layer", style="cyan")
    table.add_column("Path")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Updated")

    def _check(path: Path, label: str):
        if path.is_file():
            import os
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            size = os.path.getsize(path)
            table.add_row(label, str(path), "1", f"{size:,} B", mtime)
        elif path.is_dir():
            import os
            files = list(path.glob("*.md"))
            total_size = sum(os.path.getsize(f) for f in files)
            newest = max((os.path.getmtime(f) for f in files), default=0)
            mtime = datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M") if newest else "—"
            table.add_row(label, str(path), str(len(files)), f"{total_size:,} B", mtime)
        else:
            table.add_row(label, str(path), "—", "—", "[red]NOT FOUND[/red]")

    _check(DIGEST_FILE, "Master Digest")
    _check(NOTEBOOKLM_DIR, "Per-Project Sources")
    _check(DOMAINS_DIR, "Domain Fragments")

    gdrive = _detect_gdrive()
    if gdrive and gdrive.exists():
        _check(gdrive, "Google Drive Sync")
    else:
        table.add_row(
            "Google Drive",
            str(gdrive or "Not detected"),
            "—", "—", "[yellow]NO SYNC[/yellow]",
        )

    console.print(table)

    # Staleness warning
    if DIGEST_FILE.exists():
        import os
        age_h = (datetime.now().timestamp() - os.path.getmtime(DIGEST_FILE)) / 3600
        if age_h > 48:
            console.print(
                f"\n[red]⚠️ Digest tiene {age_h:.0f}h"
                f" — alto riesgo (>48h)[/red]"
            )
        elif age_h > 24:
            console.print(
                f"\n[yellow]⚠️ Digest tiene {age_h:.0f}h"
                f" — considerar re-sync[/yellow]"
            )
        else:
            console.print(
                f"\n[green]✅ Digest fresco ({age_h:.1f}h)[/green]"
            )
