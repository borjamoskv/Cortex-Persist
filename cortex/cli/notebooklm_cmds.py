"""
CORTEX CLI — NotebookLM Integration Commands.

Provides native CLI commands for NotebookLM synchronization:
  cortex notebooklm digest    → Generate Master Digest
  cortex notebooklm fragment  → Domain-based fragmentation
  cortex notebooklm sync      → Export to Google Drive folder
  cortex notebooklm status    → Show sync status
"""

from __future__ import annotations
from typing import Optional

import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.notebooklm_data import (
    _PROJECT_DOMAIN,
    DIGEST_FILE,
    DOMAINS_DIR,
    NOTEBOOKLM_DIR,
    _detect_cloud_sync,
    _format_fact_obj,
    _get_engine_active_facts,
    _get_entities_and_relations,
    _run_async,
    _sovereign_signature,
)

console = Console()
logger = logging.getLogger(__name__)


# ── CLI Group ──────────────────────────────────────────────────────────


@click.group("notebooklm")
def notebooklm_cmds():
    """📓 NotebookLM synchronization commands."""
    pass


@notebooklm_cmds.command("digest")
@click.option(
    "--output", "-o", type=click.Path(), default=str(DIGEST_FILE), help="Output file path"
)
def digest_cmd(output: str):
    """Generate Master Digest for NotebookLM (decrypted)."""

    async def _digest():
        facts = await _get_engine_active_facts()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        projects_data = defaultdict(list)
        for f in facts:
            projects_data[f.project].append(f)

        lines = [
            "# 🧠 CORTEX MASTER KNOWLEDGE DIGEST\n\n",
            f"> Snapshot: {ts} | Facts: {len(facts)} | Projects: {len(projects_data)}\n\n",
            "---\n\n",
        ]

        # Add Relational Graph Summary
        ents, rels = _get_entities_and_relations()
        if not ents.empty:
            lines.append("## 🕸️ Knowledge Graph Summary\n\n")
            lines.append(f"- **Total Entities**: {len(ents)}\n")
            lines.append(f"- **Active Relationships**: {len(rels)}\n\n")
            lines.append("### Top Entities (Frequent Mention)\n")
            top_ents = ents.sort_values("mention_count", ascending=False).head(10)
            for _, row in top_ents.iterrows():
                name = row["name"]
                count = row["mention_count"]
                lines.append(f"- {name} ({row['entity_type']}) - {count} mentions\n")
            lines.append("\n---\n\n")

        for proj in sorted(projects_data.keys()):
            proj_facts = projects_data[proj]
            lines.append(f"## {proj}\n*{len(proj_facts)} hechos*\n\n")

            # Group by type (O(1))
            types_data = defaultdict(list)
            for f in proj_facts:
                types_data[f.fact_type].append(f)

            for ftype in sorted(types_data.keys()):
                lines.append(f"### {ftype.capitalize()}\n\n")
                for f in types_data[ftype]:
                    lines.append(_format_fact_obj(f) + "\n\n")
            lines.append("---\n\n")

        lines.append(_sovereign_signature())
        content = "".join(lines)
        Path(output).write_text(content, encoding="utf-8")

        word_count = len(content.split())
        limit_msg = "✅ Safe" if word_count < 500_000 else "⚠️ OVER LIMIT"
        console.print(
            Panel(
                f"[green]✅ Master Digest generado (CLEAR_TEXT)[/green]\n"
                f"  Archivo: {output}\n"
                f"  Palabras: {word_count:,}\n"
                f"  {limit_msg}",
                title="📓 NotebookLM Digest",
                border_style="green",
            )
        )

    _run_async(_digest())


@notebooklm_cmds.command("fragment")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=str(DOMAINS_DIR),
    help="Output directory for domain fragments",
)
def fragment_cmd(output_dir: str):
    """Fragment decrypted knowledge into semantic domains."""

    async def _fragment():
        out = Path(output_dir)
        out.mkdir(exist_ok=True)
        facts = await _get_engine_active_facts()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Classify facts by domain (O(1) with defaultdict)
        domain_facts = defaultdict(list)
        for f in facts:
            domain = _PROJECT_DOMAIN.get(f.project, "cortex-misc")
            domain_facts[domain].append(f)

        table = Table(title="📓 Domain Fragmentation (Decrypted)")
        table.add_column("Domain", style="cyan")
        table.add_column("Facts", justify="right")
        table.add_column("Words", justify="right")
        table.add_column("Status")

        for domain in sorted(domain_facts.keys()):
            facts_in_domain = domain_facts[domain]
            filename = out / f"{domain}-{ts}.md"

            # Group by project within domain
            proj_data = defaultdict(list)
            for f in facts_in_domain:
                proj_data[f.project].append(f)

            lines = [
                f"# 🧠 CORTEX — {domain.upper()}\n\n",
                f"> Snapshot: {ts} | Facts: {len(facts_in_domain)}"
                f" | Projects: {len(proj_data)}\n\n",
                "---\n\n",
            ]

            for proj in sorted(proj_data.keys()):
                proj_facts = proj_data[proj]
                lines.append(f"## {proj}\n*{len(proj_facts)} hechos*\n\n")

                type_data = defaultdict(list)
                for f in proj_facts:
                    type_data[f.fact_type].append(f)

                for ftype in sorted(type_data.keys()):
                    lines.append(f"### {ftype.capitalize()}\n\n")
                    for f in type_data[ftype]:
                        lines.append(_format_fact_obj(f) + "\n\n")
                lines.append("---\n\n")

            lines.append(_sovereign_signature())
            content = "".join(lines)
            filename.write_text(content, encoding="utf-8")
            word_count = len(content.split())
            status = "[green]✅[/green]" if word_count < 500_000 else "[red]⚠️ OVER[/red]"
            table.add_row(domain, str(len(facts_in_domain)), f"{word_count:,}", status)

        console.print(table)
        console.print(f"\n📁 Output: {out}/")

    _run_async(_fragment())


@notebooklm_cmds.command("sync")
@click.option(
    "--drive-path",
    type=click.Path(),
    default=None,
    help="Google Drive folder path (auto-detected if not set)",
)
@click.option(
    "--mode", type=click.Choice(["digest", "domains", "both"]), default="both", help="What to sync"
)
def sync_cmd(drive_path: Optional[str], mode: str):
    """Sync exports to Google Drive for NotebookLM auto-pickup."""
    # Detect or use provided path
    if drive_path:
        target = Path(drive_path)
        provider_name = "Custom"
    else:
        detected = _detect_cloud_sync()
        if not detected:
            console.print("[red]❌ Cloud Storage no detectado (Drive/OneDrive/iCloud).[/red]")
            console.print("Especifica --drive-path manualmente.")
            return
        target, provider_name = detected

    target.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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

    # Sync Master Guide if exists
    guide = Path("cortex_notebooklm_guide.md")
    if guide.exists():
        dest = target / guide.name
        shutil.copy2(guide, dest)
        synced_files.append(str(dest))

    # Clean old files (older than 7 days)
    import time

    cutoff = time.time() - (7 * 86400)
    cleaned = 0
    for f in target.glob("*.md"):
        synced_names = [Path(s).name for s in synced_files]
        if os.path.getmtime(f) < cutoff and f.name not in synced_names:
            f.unlink()
            cleaned += 1

    console.print(
        Panel(
            f"[green]✅ Sincronizados {len(synced_files)} archivos a {provider_name}[/green]\n"
            f"  Destino: {target}\n"
            f"  {'Limpiados ' + str(cleaned) + ' archivos antiguos' if cleaned else ''}\n\n"
            f"  📋 NotebookLM debería detectarlos automáticamente\n"
            f"     si Drive está conectado como fuente.",
            title="🔄 Google Drive Sync",
            border_style="green",
        )
    )


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
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            size = os.path.getsize(path)
            table.add_row(label, str(path), "1", f"{size:,} B", mtime)
        elif path.is_dir():
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

    cloud = _detect_cloud_sync()
    if cloud:
        target, provider = cloud
        _check(target, f"{provider} Sync")
    else:
        table.add_row(
            "Cloud Sync",
            "Not detected",
            "—",
            "—",
            "[yellow]NO SYNC[/yellow]",
        )

    console.print(table)

    # Staleness warning
    if DIGEST_FILE.exists():
        age_h = (datetime.now(timezone.utc).timestamp() - os.path.getmtime(DIGEST_FILE)) / 3600
        if age_h > 48:
            console.print(f"\n[red]⚠️ Digest tiene {age_h:.0f}h — alto riesgo (>48h)[/red]")
        elif age_h > 24:
            console.print(f"\n[yellow]⚠️ Digest tiene {age_h:.0f}h — considerar re-sync[/yellow]")
        else:
            console.print(f"\n[green]✅ Digest fresco ({age_h:.1f}h)[/green]")


@notebooklm_cmds.command("ingest")
@click.option(
    "--drive-path",
    type=click.Path(),
    default=None,
    help="Google Drive folder path (auto-detected if not set)",
)
def ingest_cmd(drive_path: Optional[str]):
    """Silent daemon-like ingest: Parse NotebookLM notes back into CORTEX."""
    import json

    from cortex.cli.common import get_engine
    from cortex.extensions.llm.router import IntentProfile
    from cortex.extensions.llm.sovereign import SovereignLLM

    # Detect or use provided path
    if drive_path:
        target = Path(drive_path)
    else:
        detected = _detect_cloud_sync()
        if not detected:
            console.print("[red]❌ Cloud Storage no detectado.[/red]")
            return
        target, _ = detected

    if not target.exists():
        console.print(f"[red]❌ El directorio {target} no existe.[/red]")
        return

    manifest_path = target / ".cortex_ingest_manifest.json"
    processed_files = set()
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                processed_files = set(json.load(f))
        except (json.JSONDecodeError, OSError):
            logger.warning(
                "[NOTEBOOKLM] Manifest corrupted at %s, starting fresh.",
                manifest_path,
            )

    engine = get_engine()

    async def _ingest():
        extracted_facts = []
        newly_processed = []

        system_prompt = (
            "You are a CORTEX integration parser operating under Axiom Ω₁ (Multi-Scale Causality). "
            "Extract discrete sovereign facts (decisions, ghosts, bridges, and knowledge) "
            "from the provided NotebookLM automated summary/notes.\n"
            "CRITICAL: If the text references any previous insights containing a 'Shadow Key', "
            "which looks like '[∆_CTX:xxxxxxxx]' or '∆_CTX:xxxxxxxx' (or implies a connection to one), you MUST extract it.\n"
            "Respond ONLY with a raw JSON list of objects. No markdown formatting, "
            "no explanations.\n"
            "Do NOT include backticks (```json). Just the raw list in valid JSON.\n"
            "Format:\n"
            "[\n"
            "  {\n"
            '    "fact_type": "decision|ghost|bridge|knowledge",\n'
            '    "project": "The associated project name",\n'
            '    "content": "The actual discovery or fact extracted"'
            ",\n"
            '    "confidence": "C3",\n'
            '    "shadow_keys": ["∆_CTX:A1B2C3D4"]'
            " // Include if found, else empty list\\n"
            "  }\n"
            "]\n"
            "If no facts are present, output an empty list: []"
        )

        async with SovereignLLM() as llm:
            for file_path in target.glob("*.md"):
                # Ignoramos los propios archivos que exporta CORTEX
                if (
                    file_path.name.startswith("cortex-master")
                    or file_path.name.startswith("cortex-")
                    or file_path.name == DIGEST_FILE.name
                ):
                    continue

                if file_path.name in processed_files:
                    continue

                console.print(f"[cyan]Analizando síntesis: {file_path.name}...[/cyan]")

                content = file_path.read_text(encoding="utf-8")
                # Evita archivos inmensos que puedan saturar la ventana de contexto
                if len(content) > 50000:
                    console.print(
                        f"[yellow]⚠️  Archivo demasiado grande, saltando: {file_path.name}[/yellow]"
                    )
                    continue

                res = await llm.generate(
                    content, system=system_prompt, intent=IntentProfile.EPISODIC_PROCESSING
                )

                if res.ok:
                    try:
                        raw_json = res.content.strip()
                        if raw_json.startswith("```json"):
                            raw_json = raw_json[7:]
                        if raw_json.endswith("```"):
                            raw_json = raw_json[:-3]
                        raw_json = raw_json.strip()

                        items = json.loads(raw_json)
                        if isinstance(items, list):
                            for it in items:
                                if "content" in it and "project" in it:
                                    meta_dict = {"notebooklm_file": file_path.name}
                                    if it.get("shadow_keys"):
                                        meta_dict["shadow_keys"] = it["shadow_keys"]

                                    extracted_facts.append(
                                        {
                                            "project": it["project"],
                                            "content": it["content"],
                                            "fact_type": it.get("fact_type", "knowledge"),
                                            "confidence": it.get("confidence", "C3"),
                                            "source": "notebooklm:sync_daemon",
                                            "meta": meta_dict,
                                        }
                                    )
                            newly_processed.append(file_path.name)
                            console.print(f"   [green]→ Se extrajeron {len(items)} hechos.[/green]")
                        else:
                            console.print("   [red]→ Respuesta no es una lista JSON válida.[/red]")
                    except json.JSONDecodeError:
                        console.print(f"   [red]→ Error parseando JSON de {res.provider}[/red]")
                        console.print(f"      Raw output: {res.content[:200]}...")

        if extracted_facts:
            await engine.init_db()
            try:
                ids = await engine.store_many(extracted_facts)
                console.print(
                    Panel(
                        f"[green]✅ Ouroboros Loop Completado[/green]\n"
                        f"Hechos asimilados: {len(ids)}\n"
                        f"Archivos procesados: {len(newly_processed)}",
                        title="🧠 CORTEX Ingestion",
                        border_style="green",
                    )
                )
            finally:
                await engine.close()
        elif newly_processed:
            console.print(
                "[yellow]0 hechos extraídos, pero archivos marcados como procesados.[/yellow]"
            )
        else:
            console.print("[dim]Nada nuevo que ingerir.[/dim]")

        # Actualizar manifest
        if newly_processed:
            processed_files.update(newly_processed)
            manifest_path.write_text(json.dumps(list(processed_files), indent=2), encoding="utf-8")

    _run_async(_ingest())
